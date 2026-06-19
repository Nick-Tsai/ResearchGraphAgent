from app.pipeline.graph_builder import _parse_node_dsl, _parse_edge_dsl


def test_parse_node_dsl_reads_weak_structured_blocks():
    raw = '''# Dimension: 基本定义与数学基础
[NODE]
Type: claim
Title: 傅里叶变换原始定义与内积投影
Summary: 傅里叶变换可以视为基函数上的投影。
Evidence: ev-1, ev-2

[NODE]
Type: contradiction
Title: 连续定义与离散实现之间的张力
Summary: 理论定义与工程实现存在边界差异。
Evidence: ev-3
'''

    parsed = _parse_node_dsl(raw)

    assert len(parsed) == 2
    assert parsed[0]["node_type"] == "claim"
    assert parsed[0]["evidence_ids"] == ["ev-1", "ev-2"]
    assert parsed[1]["node_type"] == "contradiction"


def test_parse_edge_dsl_reads_relations():
    raw = '''[EDGE]
From: 基本定义与数学基础
To: 傅里叶变换原始定义与内积投影
Relation: expands
Confidence: 0.9
Reason: 维度节点展开到核心主张

[EDGE]
From: 连续定义与离散实现之间的张力
To: 傅里叶变换原始定义与内积投影
Relation: contradicts
Confidence: 0.7
Reason: 工程近似与理论定义有冲突
'''

    parsed = _parse_edge_dsl(raw)

    assert len(parsed) == 2
    assert parsed[0]["relation"] == "expands"
    assert parsed[1]["relation"] == "contradicts"
    assert parsed[1]["source_title"] == "连续定义与离散实现之间的张力"
