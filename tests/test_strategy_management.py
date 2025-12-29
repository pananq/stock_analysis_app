"""
测试策略配置管理功能
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils import get_config, setup_logging, get_logger
from app.models import get_sqlite_db
from app.services import get_strategy_service


def test_strategy_management():
    """测试策略配置管理功能"""
    logger = get_logger(__name__)
    
    logger.info("=" * 60)
    logger.info("测试策略配置管理功能")
    logger.info("=" * 60)
    
    # 获取策略服务
    strategy_service = get_strategy_service()
    
    # 1. 测试创建策略
    logger.info("\n步骤1: 测试创建策略")
    
    strategy_id1 = strategy_service.create_strategy(
        name="大涨后站稳5日线",
        description="单日涨幅超过8%，随后3天收盘价均高于5日均线",
        rise_threshold=8.0,
        observation_days=3,
        ma_period=5,
        enabled=True
    )
    
    if strategy_id1:
        logger.info(f"  ✓ 策略1创建成功，ID: {strategy_id1}")
    else:
        logger.error("  ✗ 策略1创建失败")
        return
    
    # 创建第二个策略
    strategy_id2 = strategy_service.create_strategy(
        name="温和上涨趋势",
        description="单日涨幅超过5%，随后5天收盘价均高于10日均线",
        rise_threshold=5.0,
        observation_days=5,
        ma_period=10,
        enabled=True
    )
    
    if strategy_id2:
        logger.info(f"  ✓ 策略2创建成功，ID: {strategy_id2}")
    else:
        logger.error("  ✗ 策略2创建失败")
    
    # 创建第三个策略（禁用状态）
    strategy_id3 = strategy_service.create_strategy(
        name="强势突破20日线",
        description="单日涨幅超过10%，随后3天收盘价均高于20日均线",
        rise_threshold=10.0,
        observation_days=3,
        ma_period=20,
        enabled=False
    )
    
    if strategy_id3:
        logger.info(f"  ✓ 策略3创建成功（禁用状态），ID: {strategy_id3}")
    else:
        logger.error("  ✗ 策略3创建失败")
    
    # 2. 测试参数验证
    logger.info("\n步骤2: 测试参数验证")
    
    # 测试无效的涨幅阈值
    invalid_id = strategy_service.create_strategy(
        name="无效策略1",
        rise_threshold=25.0,  # 超出范围
        observation_days=3,
        ma_period=5
    )
    
    if invalid_id is None:
        logger.info("  ✓ 正确拒绝了无效的涨幅阈值（25.0）")
    else:
        logger.error("  ✗ 未能拒绝无效的涨幅阈值")
    
    # 测试无效的观察天数
    invalid_id = strategy_service.create_strategy(
        name="无效策略2",
        rise_threshold=8.0,
        observation_days=50,  # 超出范围
        ma_period=5
    )
    
    if invalid_id is None:
        logger.info("  ✓ 正确拒绝了无效的观察天数（50）")
    else:
        logger.error("  ✗ 未能拒绝无效的观察天数")
    
    # 测试无效的均线周期
    invalid_id = strategy_service.create_strategy(
        name="无效策略3",
        rise_threshold=8.0,
        observation_days=3,
        ma_period=15  # 不在支持的列表中
    )
    
    if invalid_id is None:
        logger.info("  ✓ 正确拒绝了无效的均线周期（15）")
    else:
        logger.error("  ✗ 未能拒绝无效的均线周期")
    
    # 测试重复的策略名称
    duplicate_id = strategy_service.create_strategy(
        name="大涨后站稳5日线",  # 与策略1重名
        rise_threshold=8.0,
        observation_days=3,
        ma_period=5
    )
    
    if duplicate_id is None:
        logger.info("  ✓ 正确拒绝了重复的策略名称")
    else:
        logger.error("  ✗ 未能拒绝重复的策略名称")
    
    # 3. 测试获取策略详情
    logger.info("\n步骤3: 测试获取策略详情")
    
    strategy1 = strategy_service.get_strategy(strategy_id1)
    if strategy1:
        logger.info(f"  策略ID: {strategy1['id']}")
        logger.info(f"  策略名称: {strategy1['name']}")
        logger.info(f"  策略描述: {strategy1['description']}")
        logger.info(f"  涨幅阈值: {strategy1['config']['rise_threshold']}%")
        logger.info(f"  观察天数: {strategy1['config']['observation_days']}天")
        logger.info(f"  均线周期: {strategy1['config']['ma_period']}日")
        logger.info(f"  是否启用: {strategy1['enabled']}")
        logger.info(f"  创建时间: {strategy1['created_at']}")
        logger.info(f"  更新时间: {strategy1['updated_at']}")
        logger.info(f"  最后执行: {strategy1['last_executed_at']}")
    else:
        logger.error("  ✗ 获取策略详情失败")
    
    # 4. 测试获取策略列表
    logger.info("\n步骤4: 测试获取策略列表")
    
    all_strategies = strategy_service.list_strategies()
    logger.info(f"  所有策略数量: {len(all_strategies)}")
    
    for strategy in all_strategies:
        status = "启用" if strategy['enabled'] else "禁用"
        logger.info(f"    - {strategy['name']} ({status})")
    
    # 只获取启用的策略
    enabled_strategies = strategy_service.list_strategies(enabled_only=True)
    logger.info(f"  启用的策略数量: {len(enabled_strategies)}")
    
    # 5. 测试更新策略
    logger.info("\n步骤5: 测试更新策略")
    
    # 更新策略名称和描述
    success = strategy_service.update_strategy(
        strategy_id1,
        name="大涨后站稳5日线（修改版）",
        description="单日涨幅超过8%，随后3天收盘价均高于5日均线（已优化）"
    )
    
    if success:
        logger.info("  ✓ 策略名称和描述更新成功")
        updated_strategy = strategy_service.get_strategy(strategy_id1)
        logger.info(f"    新名称: {updated_strategy['name']}")
        logger.info(f"    新描述: {updated_strategy['description']}")
    else:
        logger.error("  ✗ 策略名称和描述更新失败")
    
    # 更新策略参数
    success = strategy_service.update_strategy(
        strategy_id2,
        rise_threshold=6.0,
        observation_days=4,
        ma_period=20
    )
    
    if success:
        logger.info("  ✓ 策略参数更新成功")
        updated_strategy = strategy_service.get_strategy(strategy_id2)
        logger.info(f"    新涨幅阈值: {updated_strategy['config']['rise_threshold']}%")
        logger.info(f"    新观察天数: {updated_strategy['config']['observation_days']}天")
        logger.info(f"    新均线周期: {updated_strategy['config']['ma_period']}日")
    else:
        logger.error("  ✗ 策略参数更新失败")
    
    # 启用禁用的策略
    success = strategy_service.update_strategy(strategy_id3, enabled=True)
    
    if success:
        logger.info("  ✓ 策略启用状态更新成功")
        updated_strategy = strategy_service.get_strategy(strategy_id3)
        logger.info(f"    新状态: {'启用' if updated_strategy['enabled'] else '禁用'}")
    else:
        logger.error("  ✗ 策略启用状态更新失败")
    
    # 6. 测试根据名称获取策略
    logger.info("\n步骤6: 测试根据名称获取策略")
    
    strategy = strategy_service.get_strategy_by_name("温和上涨趋势")
    if strategy:
        logger.info(f"  ✓ 找到策略: {strategy['name']} (ID: {strategy['id']})")
    else:
        logger.error("  ✗ 未找到策略")
    
    # 7. 测试更新最后执行时间
    logger.info("\n步骤7: 测试更新最后执行时间")
    
    success = strategy_service.update_last_execution(strategy_id1)
    if success:
        logger.info("  ✓ 最后执行时间更新成功")
        updated_strategy = strategy_service.get_strategy(strategy_id1)
        logger.info(f"    最后执行时间: {updated_strategy['last_executed_at']}")
    else:
        logger.error("  ✗ 最后执行时间更新失败")
    
    # 8. 测试删除策略
    logger.info("\n步骤8: 测试删除策略")
    
    # 删除策略3
    success = strategy_service.delete_strategy(strategy_id3)
    if success:
        logger.info(f"  ✓ 策略删除成功 (ID: {strategy_id3})")
        
        # 验证策略已被删除
        deleted_strategy = strategy_service.get_strategy(strategy_id3)
        if deleted_strategy is None:
            logger.info("  ✓ 确认策略已被删除")
        else:
            logger.error("  ✗ 策略仍然存在")
    else:
        logger.error("  ✗ 策略删除失败")
    
    # 9. 测试配置验证函数
    logger.info("\n步骤9: 测试配置验证函数")
    
    valid, msg = strategy_service.validate_strategy_config(8.0, 3, 5)
    if valid:
        logger.info("  ✓ 有效配置验证通过")
    else:
        logger.error(f"  ✗ 有效配置验证失败: {msg}")
    
    valid, msg = strategy_service.validate_strategy_config(25.0, 3, 5)
    if not valid:
        logger.info(f"  ✓ 无效配置正确拒绝: {msg}")
    else:
        logger.error("  ✗ 无效配置未被拒绝")
    
    # 10. 显示最终的策略列表
    logger.info("\n步骤10: 显示最终的策略列表")
    
    final_strategies = strategy_service.list_strategies()
    logger.info(f"  最终策略数量: {len(final_strategies)}")
    
    for strategy in final_strategies:
        status = "启用" if strategy['enabled'] else "禁用"
        config = strategy['config']
        logger.info(f"\n  策略: {strategy['name']} ({status})")
        logger.info(f"    ID: {strategy['id']}")
        logger.info(f"    描述: {strategy['description']}")
        logger.info(f"    涨幅阈值: {config['rise_threshold']}%")
        logger.info(f"    观察天数: {config['observation_days']}天")
        logger.info(f"    均线周期: {config['ma_period']}日")
        logger.info(f"    创建时间: {strategy['created_at']}")
        logger.info(f"    最后执行: {strategy['last_executed_at']}")
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ 策略配置管理测试完成！")
    logger.info("=" * 60)


def main():
    """主函数"""
    try:
        # 加载配置
        config = get_config()
        
        # 初始化日志系统
        setup_logging(config)
        logger = get_logger(__name__)
        
        logger.info("=" * 60)
        logger.info("股票分析系统 - 策略配置管理测试")
        logger.info("=" * 60)
        
        # 初始化数据库
        sqlite_db = get_sqlite_db()
        logger.info("数据库初始化完成")
        
        # 测试策略配置管理
        test_strategy_management()
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
