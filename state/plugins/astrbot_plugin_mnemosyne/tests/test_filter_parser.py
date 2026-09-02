"""
过滤器解析器测试
测试 Milvus 表达式到各数据库格式的转换
"""

import sys
from pathlib import Path

import pytest

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_filter_parser():
    """测试过滤器解析器"""
    print("\n=== 测试过滤器解析器 ===")

    from memory_manager.vector_db.filter_parser import FilterParser

    test_cases = [
        # 简单相等
        'session_id == "test_session"',
        # 数字比较
        'create_time > 1234567890',
        'create_time >= 1234567890',
        'create_time < 9999999999',
        # 不等
        'personality_id != "default"',
        # IN 操作
        'session_id in ["session1", "session2"]',
        # AND 操作
        'session_id == "test" and personality_id == "persona1"',
        # OR 操作
        'session_id == "test1" or session_id == "test2"',
        # NOT 操作
        'not session_id == "test"',
        # 复杂组合
        '(session_id == "test1" or session_id == "test2") and create_time > 1000',
    ]

    passed = 0
    failed = 0

    for expr in test_cases:
        try:
            print(f"\n✓ 测试表达式: {expr}")
            ast = FilterParser.parse(expr)
            print(f"  AST: {ast}")
            passed += 1
        except Exception as e:
            print(f"  ❌ 解析失败: {e}")
            failed += 1

    print(f"\n解析测试: {passed}/{len(test_cases)} 通过")
    assert failed == 0


def test_chroma_converter():
    """测试 Chroma 转换器"""
    print("\n=== 测试 Chroma 转换器 ===")

    from memory_manager.vector_db.filter_parser import FilterParser, ChromaFilterConverter

    test_cases = [
        ('session_id == "test"', {"session_id": {"$eq": "test"}}),
        ('create_time > 1000', {"create_time": {"$gt": 1000}}),
        ('session_id == "s1" and personality_id == "p1"',
         {"$and": [{"session_id": {"$eq": "s1"}}, {"personality_id": {"$eq": "p1"}}]}),
    ]

    passed = 0
    failed = 0

    for expr, expected_keys in test_cases:
        try:
            print(f"\n✓ 测试: {expr}")
            ast = FilterParser.parse(expr)
            chroma_filter = ChromaFilterConverter.convert(ast)
            print(f"  Chroma 格式: {chroma_filter}")

            # 简单验证（检查键是否存在）
            if isinstance(expected_keys, dict):
                for key in expected_keys.keys():
                    if key in chroma_filter or "$and" in str(chroma_filter) or "$or" in str(chroma_filter):
                        passed += 1
                        break
                else:
                    print(f"  ⚠️  键不匹配")
                    failed += 1
            else:
                passed += 1

        except Exception as e:
            print(f"  ❌ 转换失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\nChroma 转换测试: {passed}/{len(test_cases)} 通过")
    assert failed == 0


def test_qdrant_converter():
    """测试 Qdrant 转换器"""
    print("\n=== 测试 Qdrant 转换器 ===")

    try:
        from memory_manager.vector_db.filter_parser import FilterParser, QdrantFilterConverter

        test_cases = [
            'session_id == "test"',
            'create_time > 1000',
            'session_id == "s1" and personality_id == "p1"',
        ]

        passed = 0
        failed = 0

        for expr in test_cases:
            try:
                print(f"\n✓ 测试: {expr}")
                ast = FilterParser.parse(expr)
                qdrant_filter = QdrantFilterConverter.convert(ast)
                print(f"  Qdrant 格式: {qdrant_filter}")
                passed += 1
            except ImportError as e:
                print(f"  ⚠️  Qdrant 库未安装，跳过测试")
                pytest.skip("qdrant-client 未安装")
            except Exception as e:
                print(f"  ❌ 转换失败: {e}")
                failed += 1

        print(f"\nQdrant 转换测试: {passed}/{len(test_cases)} 通过")
        assert failed == 0

    except ImportError:
        print("  ⚠️  Qdrant 库未安装，跳过测试")
        pytest.skip("qdrant-client 未安装")


def test_weaviate_converter():
    """测试 Weaviate 转换器"""
    print("\n=== 测试 Weaviate 转换器 ===")

    from memory_manager.vector_db.filter_parser import FilterParser, WeaviateFilterConverter

    test_cases = [
        'session_id == "test"',
        'create_time > 1000',
        'session_id == "s1" and personality_id == "p1"',
    ]

    passed = 0
    failed = 0

    for expr in test_cases:
        try:
            print(f"\n✓ 测试: {expr}")
            ast = FilterParser.parse(expr)
            weaviate_filter = WeaviateFilterConverter.convert(ast)
            print(f"  Weaviate 格式: {weaviate_filter}")
            passed += 1
        except Exception as e:
            print(f"  ❌ 转换失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\nWeaviate 转换测试: {passed}/{len(test_cases)} 通过")
    assert failed == 0


def test_complex_expressions():
    """测试复杂表达式"""
    print("\n=== 测试复杂表达式 ===")

    from memory_manager.vector_db.filter_parser import FilterParser

    complex_cases = [
        # 多层嵌套
        '((session_id == "s1" or session_id == "s2") and personality_id == "p1") or create_time > 1000',
        # 多个 AND
        'session_id == "s1" and personality_id == "p1" and create_time > 1000',
        # NOT with OR
        'not (session_id == "s1" or session_id == "s2")',
        # IN with AND
        'session_id in ["s1", "s2", "s3"] and create_time > 1000',
    ]

    passed = 0
    failed = 0

    for expr in complex_cases:
        try:
            print(f"\n✓ 测试复杂表达式: {expr}")
            ast = FilterParser.parse(expr)
            print(f"  ✅ 解析成功")
            passed += 1
        except Exception as e:
            print(f"  ❌ 解析失败: {e}")
            failed += 1

    print(f"\n复杂表达式测试: {passed}/{len(complex_cases)} 通过")
    assert failed == 0


def main():
    """运行所有测试"""
    print("=" * 60)
    print("过滤器解析器测试套件")
    print("=" * 60)

    results = []

    # 运行测试
    for name, test_func in [
        ("过滤器解析器", test_filter_parser),
        ("Chroma 转换器", test_chroma_converter),
        ("Qdrant 转换器", test_qdrant_converter),
        ("Weaviate 转换器", test_weaviate_converter),
        ("复杂表达式", test_complex_expressions),
    ]:
        try:
            test_func()
            results.append((name, True))
        except pytest.skip.Exception:
            print(f"⚠️  跳过 - {name}")
            results.append((name, True))
        except AssertionError:
            results.append((name, False))

    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
