# test_literature_query.py
import logging
from biomni.tool import literature

# 设置日志输出到控制台
logging.basicConfig(level=logging.DEBUG)

def test_query_arxiv():
    print("==== 测试 query_arxiv ====")
    result = literature.query_arxiv("CRISPR gene editing", max_papers=2)
    print(result)
    print()

def test_query_scholar():
    print("==== 测试 query_scholar ====")
    result = literature.query_scholar("deep learning in medicine")
    print(result)
    print()

def test_query_pubmed():
    print("==== 测试 query_pubmed ====")
    result = literature.query_pubmed("cancer immunotherapy", max_papers=2)
    print(result)
    print()

def test_search_google():
    print("==== 测试 search_google ====")
    result = literature.search_google("protein folding", num_results=2)
    print(result)
    print()

if __name__ == "__main__":
    test_query_arxiv()
    test_query_scholar()
    test_query_pubmed()
    test_search_google()