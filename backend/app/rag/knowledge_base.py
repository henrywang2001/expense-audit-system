"""
知识库管理器
加载和管理财务审核领域的初始知识文档
"""
import logging
from typing import List, Dict, Any, Optional

from app.rag.embeddings import DashScopeEmbeddings
from app.rag.vectorstore import ChromaVectorStore

logger = logging.getLogger(__name__)

# 财务审核领域的初始知识文档
FINANCIAL_KNOWLEDGE = [
    # 差旅费相关
    {
        "content": "差旅费报销管理规范：员工因公出差产生的交通费、住宿费、伙食补助等费用，需在出差结束后10个工作日内提交报销申请。交通费标准：高铁二等座、飞机经济舱。住宿费标准：一线城市（北京、上海、广州、深圳）不超过500元/天，其他城市不超过350元/天。出差补贴：一线城市100元/天，其他城市80元/天。",
        "metadata": {"category": "travel", "type": "policy", "source": "公司差旅管理办法"},
    },
    {
        "content": "差旅费报销所需材料：1）出差审批单或出差申请记录；2）往返交通票据（机票行程单、火车票等）；3）住宿发票（增值税普通发票或专用发票）；4）出差行程说明；5）如有招待费需单独填写招待费申请。所有票据需清晰完整，不得涂改。",
        "metadata": {"category": "travel", "type": "requirements", "source": "报销须知"},
    },
    # 招待费相关
    {
        "content": "招待费管理规定：招待费是指因业务需要宴请客户、合作伙伴等产生的餐饮费用。招待费需提前填写《业务招待费申请表》，注明招待对象、事由、参与人员及预估金额，经部门负责人审批后方可执行。招待标准：人均不超过200元，单次总额不超过2000元。超过标准的需提前报总经理审批。",
        "metadata": {"category": "entertainment", "type": "policy", "source": "公司招待费管理办法"},
    },
    {
        "content": "招待费报销注意事项：1）必须附有正规餐饮发票；2）需提供《业务招待费申请表》原件；3）单次消费超过1000元需提供消费明细清单；4）严禁以招待费名义报销个人聚餐费用；5）不得报销烟酒等高档消费品。违反上述规定的不予报销。",
        "metadata": {"category": "entertainment", "type": "restrictions", "source": "报销审核要点"},
    },
    # 办公费相关
    {
        "content": "办公用品采购和报销规定：日常办公用品（文具、纸张、墨盒等）由行政部门统一采购，各部门按月申报需求。紧急采购需填写《紧急采购申请表》，经部门经理审批后可在限额内自行采购并报销。单价超过500元或批量采购超过2000元的需走正式采购流程。",
        "metadata": {"category": "office", "type": "policy", "source": "办公用品管理制度"},
    },
    {
        "content": "固定资产采购标准：单价超过2000元且使用年限超过1年的设备属于固定资产，需填写《固定资产采购申请表》，经部门负责人、财务部、总经理三级审批。采购后需在行政部门登记，粘贴固定资产标签。报销时需提供采购合同、发票和固定资产登记表。",
        "metadata": {"category": "equipment", "type": "policy", "source": "固定资产管理办法"},
    },
    # 通用规则
    {
        "content": "发票要求：1）所有报销必须提供合法有效的发票；2）增值税专用发票需包含完整的购方信息（公司名称、税号、地址、电话、开户行及账号）；3）发票日期必须在费用发生日期前30天至后30天内；4）发票金额需与报销金额一致；5）不得使用过期、涂改、伪造发票。发票验证通过后方可进入审批流程。",
        "metadata": {"category": "general", "type": "requirements", "source": "发票管理规定"},
    },
    {
        "content": "报销审批流程：1）金额500元以下：部门经理一级审批；2）500-2000元：部门经理+财务主管二级审批；3）2000-5000元：部门经理+财务主管+分管副总三级审批；4）5000元以上：三级审批+总经理审批。所有审批需在3个工作日内完成。审批不通过的需明确说明理由。",
        "metadata": {"category": "general", "type": "process", "source": "审批流程规范"},
    },
    {
        "content": "违规行为处理：以下行为视为严重违规，除不予报销外将按公司纪律处分：1）伪造、变造发票或票据；2）同一发票重复报销；3）虚报费用金额；4）将个人消费伪装为公务支出；5）未经审批擅自超标准消费。一年内累计违规2次以上将影响个人绩效考核和晋升。",
        "metadata": {"category": "general", "type": "penalties", "source": "员工行为规范"},
    },
    {
        "content": "常见审核要点清单：检查发票真伪和完整性，核对发票金额与报销金额是否一致，确认费用类别是否选择正确，检查是否超出预算标准，核实是否在审批流程完成后方可付款，关注大额异常报销，检查历史记录是否存在相似报销，核实报销人与费用实际使用者是否一致。",
        "metadata": {"category": "general", "type": "checklist", "source": "审核员手册"},
    },
    # 培训费相关
    {
        "content": "培训费用报销规定：员工参加外部培训需提前提交《培训申请表》，内容包括培训目的、课程内容、费用预算等。培训费用包括培训费、教材费、交通费和住宿费。培训费用标准：技术类培训不超过5000元/人次，管理类培训不超过8000元/人次。培训结束后需提交培训总结报告。",
        "metadata": {"category": "training", "type": "policy", "source": "培训管理制度"},
    },
    # 交通费相关
    {
        "content": "市内交通费报销规定：因公务产生的市内交通费据实报销，优先使用公共交通（地铁、公交）。出租车费用需注明起止地点和事由。网约车费用需通过公司统一账号叫车。私车公用需提前申请，按1.5元/公里标准报销油费和过路费。每月市内交通费总额不超过800元。",
        "metadata": {"category": "transport", "type": "policy", "source": "交通费管理办法"},
    },
    # 餐饮费相关
    {
        "content": "加班餐费报销规定：工作日加班超过2小时可报销餐费，标准为30元/人；周末加班可报销午餐和晚餐，标准为50元/人/餐。加班餐费需附加班审批记录，注明加班日期、时间和事由。多人加班需统一订餐，由一人提交报销。严禁将日常餐饮费用以加班餐费名义报销。",
        "metadata": {"category": "meal", "type": "policy", "source": "加班餐费管理规定"},
    },
]


class KnowledgeBaseManager:
    """
    知识库管理器

    负责加载初始知识文档、更新和查询知识库
    """

    def __init__(self, vector_store: ChromaVectorStore = None):
        """
        初始化知识库管理器

        Args:
            vector_store: 向量存储实例
        """
        self.vector_store = vector_store or ChromaVectorStore()
        self.embeddings = DashScopeEmbeddings()

    def initialize_knowledge_base(self) -> int:
        """
        初始化知识库，加载预定义的基础财务知识文档

        Returns:
            加载的文档数量
        """
        logger.info("开始初始化知识库...")

        collection = self.vector_store.get_or_create_collection()
        existing_count = collection.count()

        if existing_count > 0:
            logger.info(f"知识库已存在 {existing_count} 条文档，跳过初始化")
            return existing_count

        # 准备文档
        documents = [item["content"] for item in FINANCIAL_KNOWLEDGE]
        metadatas = [item["metadata"] for item in FINANCIAL_KNOWLEDGE]
        ids = [f"kb_{i}" for i in range(len(documents))]

        # 向量化文档
        try:
            embeddings = self.embeddings.embed_documents(documents)
        except Exception as e:
            logger.warning(f"生成嵌入向量失败，将由 ChromaDB 自动处理: {e}")
            embeddings = None

        # 添加到向量存储
        self.vector_store.add_documents(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings,
        )

        logger.info(f"知识库初始化完成，共加载 {len(documents)} 条文档")
        return len(documents)

    def add_knowledge(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """
        向知识库添加新文档

        Args:
            documents: 文档文本列表
            metadatas: 元数据列表

        Returns:
            添加的文档数量
        """
        ids = self.vector_store.add_documents(
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(f"向知识库添加了 {len(ids)} 条新文档")
        return len(ids)

    def search_knowledge(
        self, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        检索知识库

        Args:
            query: 查询文本
            top_k: 返回结果数

        Returns:
            相关知识文档列表
        """
        return self.vector_store.search(query=query, top_k=top_k)

    def get_stats(self) -> dict:
        """获取知识库统计信息"""
        return self.vector_store.get_collection_stats()

    def reset(self):
        """重置知识库"""
        self.vector_store.reset()
        logger.info("知识库已重置")

    def get_all_categories(self) -> List[str]:
        """获取所有知识类别"""
        categories = set()
        for item in FINANCIAL_KNOWLEDGE:
            categories.add(item["metadata"]["category"])
        return sorted(list(categories))
