import datetime
from enum import Enum

from utils.motor import L
from mongoengine import *
from mongoengine.document import Document
from mongoengine.fields import *
from models.comment import Comment
from models.user import User
from models.problem import Problem
from models.submission import Submission
from models.mixin.asyncable import Asyncable
from mongoengine.queryset import *
from mongoengine.document import EmbeddedDocument
# 假设1：比赛时要求高度实时性，必须缓存Participation以便利用索引看榜
# 假设2：VP时不需要太高的性能要求，可以在赛时按时间拼表查询Submission计算排行榜

# 比赛交题：Participation拼Contest拼Submission -> 算max_submissions以及时间区间是否合标 然后才能提交 (2RTT)
# 判题完成：查询Contest拼所有Submission -> 更新Participation (2RTT) (Done)
# 看排行榜：用索引排行Participation
# 看solved/tried数：查Contest拼Participation拼Submission (Done)
# {problems:[], parts:[subs:[]]}
class ContestProblem(EmbeddedDocument):
    """比赛状态的问题"""
    problem = ReferenceField(Problem, required=True)
    alias_name = StringField() # 短题名，像是A、B、C、D1、D2这种

    # solved = IntField(default=0) # 这俩用groupBy做
    # tried = IntField(default=0)

    max_submissions = IntField() # 提交次数限制

    penalty = IntField() # acm赛制下对于此问题每个错误提交罚时多少秒，或cf赛制下每个错误提交扣多少分
    # IOI用
    points = FloatField() # IOI用赋分
    partial = BooleanField() # 部分分选项，如字段存在即为True
    # CF用
    is_pretested = BooleanField()
    devalued_points = FloatField() # 至比赛结束提交时的贬值分数，中间用线性插值算当前时刻的分数
    min_points = FloatField() # CF赛制下写对这题至少能得几分

class ContestType(Enum):
    ACM = 'acm'
    IOI = 'ioi'
    CODEFORCES = 'cf'

class Contest(Document, Asyncable):
    """比赛"""
    SCOREBOARD_VISIBLE = 'V'
    SCOREBOARD_AFTER_CONTEST = 'C'
    SCOREBOARD_AFTER_PARTICIPATION = 'P'
    SCOREBOARD_HIDDEN = 'H'
    SCOREBOARD_VISIBILITY = (
        (SCOREBOARD_VISIBLE, 'Visible'),
        (SCOREBOARD_AFTER_CONTEST, 'Hidden for duration of contest'),
        (SCOREBOARD_AFTER_PARTICIPATION, 'Hidden for duration of participation'),
        (SCOREBOARD_HIDDEN, 'Hidden permanently'),
    )
    # meta = {'allow_inheritance': True}
    poster = LazyReferenceField(Comment, reverse_delete_rule=DO_NOTHING)

    id = StringField(primary_key=True)
    name = StringField()
    type = StringField(required=True) # 比赛类型，参见ContestType

    authors = ListField(LazyReferenceField(User, reverse_delete_rule=PULL))
    curators = ListField(LazyReferenceField(User, reverse_delete_rule=PULL))

    problems = EmbeddedDocumentListField(ContestProblem)
    
    start_time = DateTimeField(required=True)
    end_time = DateTimeField(required=True)
    lock_after = DateTimeField()

    is_visible = BooleanField(default=False) # 在比赛list中展示
    is_rated = BooleanField()
    rate_all = BooleanField()
    rating_floor = IntField()
    rating_ceiling = IntField()

    run_pretests_only = BooleanField(default=False)

    is_private = BooleanField(default=False) # 是否带密码
    access_code = StringField() # 访问密码

    @classmethod
    async def get_solved_tried(cls, pk):
        """拿排行榜的解决/尝试信息，解决指每个已经AC的选手最多算一次，尝试指每道题的提交次数"""
        results = await ContestParticipation.aaggregate_list([
            {'$match': {'contest': pk}},
            {'$project':{
                '_id': 1
            }},{'$lookup': {
                'from':Submission._get_collection_name(),
                'localField': '_id',
                'foreignField': 'participation',
                'as': 'sub'
            }},{'$project':{
                '_id':0,
                'sub.result':1,
                'sub.problem':1,
                'sub.participation':1,
            }},{'$unwind': {'path': '$sub'}},
            {'$facet':{
                'tried': [
                    {'$group': {'_id': '$sub.problem', 'cnt': {'$count': {}}}}
                ],
                'solved': [
                    {'$match': {'sub.result': 'AC'}},
                    {'$group': {'_id': {'pro':'$sub.problem', 'part':'$sub.participation'}}},
                    {'$group': {'_id': '$_id.pro', 'pass': {'$count': {}}}},
                ]
            }}
        ])[0]
        tried_data = {i['_id']:i['cnt'] for i in results['tried']}
        solved_data = {i['_id']:i['pass'] for i in results['solved']}
        return solved_data, tried_data



class ContestParticipation(Document, Asyncable):
    """用户的比赛注册信息，排行榜上就排这玩意，每个用户对于每个比赛只能同时最多拥有一个
    
    为了避免比赛时大并发量导致查库是不是有预处理然后缓存在内存中然后查询时直接返回的必要？
    
    如果有，存内存中还是数据库中？
    
    存数据库中如何保障分页？和没做改变之前有什么区别？能不能在这基础上修改？
    
    存内存中如何保证多worker部署不出问题？内存是否足够应付数万人参与的比赛？"""
    contest = LazyReferenceField(Contest, reverse_delete_rule=CASCADE)
    # submissions = ListField(LazyReferenceField(Submission, reverse_delete_rule=PULL)) # 这个可以直接submission查
    submissions = ListField(DictField()) # 存提交具体信息，避免反复拼表
    user = LazyReferenceField(User, reverse_delete_rule=CASCADE)

    # 这两个赛时排行因为不得不查询submission所以没有维护的必要
    score = FloatField(default=0) # [要上索引] IOI或CF分数 赛时检索用
    solved = IntField(default=0) # [要上索引] ACM解出题数 赛时检索用
    cumtime = FloatField(default=0) # [要上索引] 罚时
    real_start = DateTimeField() # 比赛实际开始时间，VP用

    is_disqualified = BooleanField(default=False) # 是否被取消资格/打星
    virtual = IntField(default=0) # 0表示正常参赛，1以上表示第几轮VP

    format_data = DictField() # 留作后用

    @classmethod
    async def update_submission_cache(cls, pk):
        """2RTT，维护当前时间下的score、solved、cumtime、submissions信息"""
        results = await cls.aaggregate_list([
            {'$match': {'_id': pk}},
            {'$lookup': {
                'from': Contest._get_collection_name(),
                'localField': 'contest',
                'foreignField': '_id',
                'as': 'contest'
            }},{'$lookup':{
                'from': Submission._get_collection_name(),
                'localField': '_id',
                'foreignField': 'participation',
                'as': 'submission_data'
            }},{'$project':{
                '_id': False,
                'submission_data._id': True,
                'submission_data.problem': True,
                'submission_data.error': True,
                'submission_data.result': True,
                'submission_data.points': True,
                'submission_data.date': True,
                'submission_data.case_points': True,
                'submission_data.case_total': True,
                'contest.problems': True,
                'contest.type': True,
                'contest.start_time': True,
                'contest.end_time': True,
                'contest.lock_after': True,
                'real_start': True,
            }}
        ])[0]

        contest = results['contest'][0]
        end = contest['end_time']
        if (lock_after:=contest.get('lock_after')) is not None:
            if end > datetime.datetime.now() > lock_after:
                return # 封榜时不更新

        contest_type = contest['type']
        real_start = results['real_start']
        start = contest['start_time']
        contest_length = (end - start).total_seconds()

        submissions = sorted(results['submission_data'], key=lambda x:x['date'])
        problems = contest['problems']
        pmeta = {x['_id']:{} for x in problems}
        pinfo = {x['_id']:x for x in problems}

        def lerp(a, b, t): return b * t + (1 - t) * a

        for sub in submissions:
            pid = sub['problem']
            problem = pinfo[pid]
            result = sub['result']
            if result in ('CE', 'IE'):
                continue
            if result == 'AC':
                if 'cumtime' not in pmeta[pid]: # acm
                    pmeta[pid]['cumtime'] = problem.get('penalty', 1200) * pmeta[pid].get('try', 0) + (
                        sub['date'] - results['real_start']).total_seconds()
                if (points := problem.get('points')) is not None: # ioi
                    pmeta[pid]['ioiscore'] = points
                if (devalued := problem.get('devalued_points')) is not None: # cf 最后一次正确提交
                    pmeta[pid]['cfscore'] = max(
                        problem.get('min_points', 0),
                        lerp(points, devalued, (sub['date']-start).total_seconds()/contest_length)
                        - problem.get('penalty', 50) * pmeta[pid].get('try', 0)
                    )
            else:

                if problem.get('partial') is not None and (points := problem.get('points')) is not None:
                    if (partial_points := sub.get('points') is not None):
                        pmeta[pid]['ioiscore'] = max(pmeta[pid].get('ioiscore',0), points * partial_points / sub['case_total'])
                    else:
                        pmeta[pid]['ioiscore'] = max(pmeta[pid].get('ioiscore',0), points * sub['case_points'] / sub['case_total'])

            pmeta[pid]['try'] = pmeta[pid].get('try', 0) + 1
        
        sum_cumtime = 0
        sum_points = 0
        sum_solved = 0

        for pid, data in pmeta.items():
            if contest_type == 'cf':
                sum_points += data['cfscore']
            else:
                sum_points += data.get('ioiscore', 0)
            if (c := data.get('cumtime') is not None):
                sum_cumtime += c
                sum_solved += 1
        return (await cls.aupdate_one(
            {'_id': pk},
            {'$set': {
                'submissions': submissions,
                'cumtime': sum_cumtime,
                'solved': sum_solved,
                'score': sum_points
            }},
        ))

            

        # .objects(participation=pk)
        #     .only('id', 'problem', 'points', 'result'))

    # 还需要知道是哪题的不然不能算score和solved和cumtime    
    # @classmethod
    # async def after_submission(cls, submission: Submission):
    #     """题交结束的后处理，推入一个Submission"""
    #     await (cls.aupdate_one(
    #         {'_id': submission.participation.pk},
    #         {'$push': {'submissions': submission.to_mongo()}}
    #     ))
        # await (cls.aupdate_one(
        #     {'_id': submission.participation.pk},
        #     {'$set': {'submissions.$[element]': submission.to_mongo()}},
        #     {'arrayFilters':[{'element':{'_id': submission.pk}}]}
        # ))
    

# class ScoreboardEvent(Document, Asyncable):
#     """排行榜过题人数辅助文档，为了避免大表拼接与处理而设计
    
#     还要额外维护，有必要吗？"""
#     contest = LazyReferenceField(Contest, reverse_delete_rule=CASCADE) # 上索引，可以是hash索引
#     participation = LazyReferenceField(ContestParticipation, reverse_delete_rule=DO_NOTHING)
#     problem = LazyReferenceField(Problem, reverse_delete_rule=DO_NOTHING)
#     date = DateTimeField()
#     status = StringField()
#     score = IntField()

class Rating(Document, Asyncable):
    participation = ReferenceField(ContestParticipation, reverse_delete_rule=CASCADE)
    rank = IntField()
    rating = IntField()

