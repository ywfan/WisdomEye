"""Sample resume data for testing."""

SAMPLE_RESUME_TEXT_CN = """
张三
高级算法工程师

联系方式
电话：138-0000-0000
邮箱：zhangsan@example.com
地址：北京市海淀区

教育背景
2018-2022  清华大学  计算机科学与技术  博士
  导师：李四教授
  研究方向：深度学习、自然语言处理
  
2014-2018  北京大学  软件工程  学士
  专业排名：3/120

工作经历
2022-至今  字节跳动  算法工程师
  负责推荐系统算法优化
  
研究方向
- 大语言模型
- 推荐系统
- 计算机视觉

论文发表
1. Attention Is All You Need. NeurIPS 2017. (引用: 50000+)
2. BERT: Pre-training of Deep Bidirectional Transformers. NAACL 2019.

获奖情况
2021年  国家奖学金
2020年  ACM SIGKDD最佳论文奖

技能
编程语言: Python, C++, Java
框架: PyTorch, TensorFlow, JAX
工具: Git, Docker, Kubernetes
"""

SAMPLE_RESUME_TEXT_EN = """
John Doe
Senior Machine Learning Engineer

Contact
Email: john.doe@example.com
Phone: +1-555-0123
Location: San Francisco, CA

Education
2018-2022  Stanford University  Computer Science  Ph.D.
  Advisor: Prof. Jane Smith
  Focus: Deep Learning, Natural Language Processing
  
2014-2018  MIT  Computer Science  B.S.
  GPA: 3.9/4.0

Work Experience
2022-Present  Google Research  Research Scientist
  - Leading language model research
  - Published 5 papers at top-tier conferences
  
2020-2022  OpenAI  Research Intern
  - Contributed to GPT-3 development

Research Interests
- Large Language Models
- Multimodal Learning
- Efficient Neural Architectures

Publications
1. Transformer-XL: Attentive Language Models. ACL 2019.
2. ELECTRA: Pre-training Text Encoders. ICLR 2020.

Awards
2021  Outstanding Paper Award, NeurIPS
2020  Best Thesis Award, Stanford CS Department

Skills
Languages: Python, C++, Julia
Frameworks: PyTorch, JAX, Flax
"""

SAMPLE_JSON_MINIMAL = {
    "basic_info": {
        "name": "测试用户",
        "highest_degree": "博士",
        "contact": {
            "email": "test@example.com",
            "phone": "",
            "location": "",
            "homepage": ""
        },
        "summary": "",
        "academic_metrics": {}
    },
    "education": [],
    "publications": [],
    "awards": []
}

SAMPLE_JSON_COMPLETE = {
    "basic_info": {
        "name": "张三",
        "highest_degree": "博士",
        "contact": {
            "phone": "138-0000-0000",
            "email": "zhangsan@example.com",
            "location": "北京",
            "homepage": "https://zhangsan.ai"
        },
        "summary": "资深AI研究者",
        "academic_metrics": {
            "h_index": "25",
            "citations_total": "5000",
            "citations_recent": "2000"
        }
    },
    "research_interests": ["深度学习", "NLP"],
    "education": [
        {
            "school": "清华大学",
            "degree": "博士",
            "major": "计算机科学",
            "time_period": "2018-2022",
            "supervisor": "李四",
            "thesis_title": "基于Transformer的文本生成研究",
            "details": ""
        }
    ],
    "publications": [
        {
            "title": "Attention Is All You Need",
            "authors": ["Vaswani", "Shazeer"],
            "venue": "NeurIPS 2017",
            "status": "Published",
            "url": "https://arxiv.org/abs/1706.03762",
            "abstract": "The dominant sequence transduction models...",
            "summary": "提出了Transformer架构",
            "date": "2017"
        }
    ],
    "awards": [
        {
            "name": "国家奖学金",
            "date": "2021",
            "intro": "教育部设立的最高荣誉奖学金"
        }
    ],
    "skills": {
        "tech_stack": ["Python", "PyTorch", "TensorFlow"],
        "languages": ["中文", "英文"]
    }
}
