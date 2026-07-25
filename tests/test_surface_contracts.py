"""页面、API、后台任务和 MCP 表面契约回归测试。"""

import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

import pandas as pd
from flask import Flask, g

from app.api.json_provider import CustomJSONProvider


class FakeHttpResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {'success': True, 'data': {}}

    def json(self):
        return self._payload


def make_api_app(blueprint, prefix):
    app = Flask(__name__)
    app.json = CustomJSONProvider(app)
    app.config['TESTING'] = True
    app.register_blueprint(blueprint, url_prefix=prefix)

    @app.before_request
    def set_user():
        g.user = {'user_id': 1, 'username': 'admin', 'role': 'admin'}

    return app


class StockRouteContractTests(unittest.TestCase):
    def setUp(self):
        from app.api.routes.stock_routes import stock_bp

        self.app = make_api_app(stock_bp, '/api/stocks')
        self.client = self.app.test_client()

    def test_latest_uses_market_and_security_type_aware_service(self):
        class FakeSecurityData:
            def __init__(self):
                self.call = None

            def get_daily_data(self, *args, **kwargs):
                self.call = (args, kwargs)
                return pd.DataFrame([{
                    'code': 'QQQ',
                    'market': 'US',
                    'security_type': 'ETF',
                    'trade_date': '2026-07-24',
                    'close': 600.5,
                }])

        service = FakeSecurityData()
        with patch(
            'app.api.routes.stock_routes.get_security_market_data_service',
            return_value=service,
        ):
            response = self.client.get(
                '/api/stocks/QQQ/latest?market=US&security_type=ETF'
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['data']['market'], 'US')
        self.assertEqual(service.call[1]['security_type'], 'ETF')
        self.assertEqual(service.call[1]['limit'], 1)

    def test_market_update_calls_supported_service_method(self):
        with patch(
            'app.api.routes.stock_routes.create_exclusive_background_task',
            return_value='task-market-update',
        ) as create_task:
            response = self.client.post(
                '/api/stocks/market-data/update',
                json={'days': 7},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['task_id'], 'task-market-update')
        self.assertEqual(create_task.call_args.kwargs['kwargs'], {
            'days': 7,
            'only_existing': False,
            'markets': ['CN', 'HK', 'US'],
        })

    def test_stats_uses_existing_statistics_method(self):
        class FakeStocks:
            def count_stocks(self, **kwargs):
                return 10 if not kwargs else 2

        class FakeMarketData:
            def get_data_statistics(self):
                return {'stock_count': 2, 'total_records': 20}

        with (
            patch(
                'app.api.routes.stock_routes.get_stock_service',
                return_value=FakeStocks(),
            ),
            patch(
                'app.api.routes.stock_routes.get_market_data_service',
                return_value=FakeMarketData(),
            ),
        ):
            response = self.client.get('/api/stocks/stats')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()['data']['market_data']['total_records'],
            20,
        )

    def test_stock_directory_import_and_update_handlers(self):
        with patch(
            'app.api.routes.stock_routes.create_exclusive_background_task',
            side_effect=['task-update', 'task-import'],
        ) as create_task:
            updated = self.client.post('/api/stocks/update')
            imported = self.client.post('/api/stocks/list/import')

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(imported.status_code, 200)
        self.assertEqual(updated.get_json()['task_id'], 'task-update')
        self.assertEqual(imported.get_json()['task_id'], 'task-import')
        self.assertEqual(create_task.call_count, 2)

    def test_invalid_pagination_and_dates_return_400(self):
        self.assertEqual(
            self.client.get('/api/stocks?limit=abc').status_code,
            400,
        )
        self.assertEqual(
            self.client.get(
                '/api/stocks/QQQ/daily?start_date=2026-08-01'
                '&end_date=2026-07-01'
            ).status_code,
            400,
        )

    def test_industry_filter_is_forwarded_to_stock_service(self):
        class FakeStocks:
            def __init__(self):
                self.list_kwargs = None
                self.count_kwargs = None

            def list_stocks(self, **kwargs):
                self.list_kwargs = kwargs
                return []

            def count_stocks(self, **kwargs):
                self.count_kwargs = kwargs
                return 0

        service = FakeStocks()
        with patch(
            'app.api.routes.stock_routes.get_stock_service',
            return_value=service,
        ):
            response = self.client.get('/api/stocks?industry=银行')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(service.list_kwargs['industry'], '银行')
        self.assertEqual(service.count_kwargs['industry'], '银行')

    def test_keyword_filters_are_grouped_and_paginated_in_sql(self):
        from app.services.stock_service import StockService

        class FakeDb:
            def __init__(self):
                self.query = None
                self.params = None

            def execute_query(self, query, params=None):
                self.query = ' '.join(query.split())
                self.params = params
                return []

        service = StockService.__new__(StockService)
        service.db = FakeDb()
        service.search_stocks(
            'QQQ',
            market='US',
            security_type='ETF',
            industry='Technology',
            limit=20,
            offset=40,
        )

        self.assertIn(
            'WHERE (code LIKE %s OR name LIKE %s)',
            service.db.query,
        )
        self.assertIn('AND security_type = %s', service.db.query)
        self.assertIn('AND industry LIKE %s', service.db.query)
        self.assertIn('LIMIT %s OFFSET %s', service.db.query)
        self.assertEqual(service.db.params[-2:], (20, 40))


class APIAuthenticationContractTests(unittest.TestCase):
    def setUp(self):
        from app.api.app import register_request_hooks

        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        register_request_hooks(self.app)

        @self.app.get('/api/protected')
        def protected():
            return {'user': g.user}

        self.client = self.app.test_client()

    def test_same_origin_browser_cookie_is_accepted(self):
        payload = {'user_id': 1, 'username': 'admin', 'role': 'admin'}
        self.client.set_cookie('auth_token', 'browser-cookie-token')

        with patch(
            'app.utils.auth.AuthUtils.verify_token',
            return_value=payload,
        ) as verify:
            response = self.client.get('/api/protected')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['user'], payload)
        verify.assert_called_once_with('browser-cookie-token')

    def test_missing_cookie_and_bearer_token_are_rejected(self):
        response = self.client.get('/api/protected')
        self.assertEqual(response.status_code, 401)


class DataTaskContractTests(unittest.TestCase):
    def setUp(self):
        from app.api.routes.data_routes import data_bp

        self.app = make_api_app(data_bp, '/api/data')
        self.client = self.app.test_client()

    def test_import_and_update_options_are_attached_to_tasks(self):
        with patch(
            'app.api.routes.data_routes.create_exclusive_background_task',
            side_effect=['task-1', 'task-2'],
        ) as create_task:
            imported = self.client.post('/api/data/import', json={
                'start_date': '2026-01-01',
                'end_date': '2026-07-25',
                'limit': 25,
                'skip': 3,
            })
            updated = self.client.post('/api/data/update', json={
                'days': 9,
                'only_existing': False,
            })

        self.assertEqual(imported.status_code, 200)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(create_task.call_args_list[0].kwargs['kwargs'], {
            'start_date': '2026-01-01',
            'end_date': '2026-07-25',
            'limit': 25,
            'skip': 3,
            'markets': ['CN', 'HK', 'US'],
        })
        self.assertEqual(create_task.call_args_list[1].kwargs['kwargs'], {
            'days': 9,
            'only_existing': False,
            'markets': ['CN', 'HK', 'US'],
        })

    def test_task_wrappers_forward_options_to_market_service(self):
        from app.services import data_task_jobs

        class FakeScheduler:
            def _log_job_start(self, *args):
                return 1

            def _log_job_success(self, *args):
                return None

            def _log_job_error(self, *args):
                return None

            def log_task_detail(self, **kwargs):
                return None

        class FakeMarketData:
            def __init__(self):
                self.import_kwargs = None
                self.update_kwargs = None

            def import_all_history(self, **kwargs):
                self.import_kwargs = kwargs
                return {'success': True}

            def update_recent_data(self, **kwargs):
                self.update_kwargs = kwargs
                return {'success': True}

        service = FakeMarketData()
        scheduler = FakeScheduler()
        with (
            patch(
                'app.services.get_market_data_service',
                return_value=service,
            ),
            patch(
                'app.scheduler.get_task_scheduler',
                return_value=scheduler,
            ),
        ):
            data_task_jobs.execute_full_import(
                start_date='2026-01-01',
                end_date='2026-02-01',
                limit=4,
                skip=2,
                markets=['CN', 'HK', 'US'],
                stop_event='stop',
            )
            data_task_jobs.execute_recent_update(
                days=12,
                only_existing=False,
                markets=['CN', 'HK', 'US'],
                stop_event='stop',
            )

        self.assertEqual(service.import_kwargs['limit'], 4)
        self.assertEqual(service.import_kwargs['skip'], 2)
        self.assertEqual(
            service.import_kwargs['markets'],
            ['CN', 'HK', 'US'],
        )
        self.assertEqual(service.update_kwargs['days'], 12)
        self.assertFalse(service.update_kwargs['only_existing'])
        self.assertEqual(
            service.update_kwargs['markets'],
            ['CN', 'HK', 'US'],
        )

    def test_invalid_task_options_return_400_without_starting_task(self):
        class FakeTasks:
            def list_tasks(self, status=None):
                return []

        with patch(
            'app.api.routes.data_routes.get_task_manager',
            return_value=FakeTasks(),
        ):
            invalid_date = self.client.post(
                '/api/data/import',
                json={'start_date': 'not-a-date'},
            )
            invalid_days = self.client.post(
                '/api/data/update',
                json={'days': 0},
            )
        self.assertEqual(invalid_date.status_code, 400)
        self.assertEqual(invalid_days.status_code, 400)

    def test_existing_only_update_is_rejected_to_preserve_market_coverage(self):
        class FakeTasks:
            def list_tasks(self, status=None):
                return []

        with patch(
            'app.api.routes.data_routes.get_task_manager',
            return_value=FakeTasks(),
        ):
            response = self.client.post(
                '/api/data/update',
                json={'only_existing': True},
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn('港股和美股', response.get_json()['error'])

    def test_data_status_failure_is_not_reported_as_success(self):
        class FailingMarketData:
            def get_data_statistics(self):
                raise RuntimeError('database password should stay private')

        with patch(
            'app.api.routes.data_routes.get_market_data_service',
            return_value=FailingMarketData(),
        ):
            response = self.client.get('/api/data/status')

        self.assertEqual(response.status_code, 500)
        self.assertFalse(response.get_json()['success'])
        self.assertNotIn('password', response.get_data(as_text=True))


class DataTaskCoordinatorContractTests(unittest.TestCase):
    def setUp(self):
        from app.services.data_task_coordinator import DataTaskCoordinator

        class FakeLockDb:
            def __init__(self):
                self.row = None

            def execute_update(self, sql, params=None):
                normalized = ' '.join(sql.split()).upper()
                if normalized.startswith('CREATE TABLE'):
                    return 0
                if normalized.startswith('INSERT IGNORE INTO DATA_TASK_LOCKS'):
                    if self.row is not None:
                        return 0
                    (
                        _lock_name,
                        token,
                        task_type,
                        task_name,
                        source,
                        owner_pid,
                        acquired_at,
                    ) = params
                    self.row = {
                        'token': token,
                        'task_id': None,
                        'task_type': task_type,
                        'task_name': task_name,
                        'source': source,
                        'owner_pid': owner_pid,
                        'started_at': acquired_at,
                    }
                    return 1
                if normalized.startswith('UPDATE DATA_TASK_LOCKS'):
                    task_id, _lock_name, token = params
                    if self.row and self.row['token'] == token:
                        self.row['task_id'] = task_id
                        return 1
                    return 0
                if normalized.startswith('DELETE FROM DATA_TASK_LOCKS'):
                    _lock_name, token = params
                    if self.row and self.row['token'] == token:
                        self.row = None
                        return 1
                    return 0
                raise AssertionError(sql)

            def execute_query(self, sql, params=None):
                return [dict(self.row)] if self.row else []

        self.lock_db = FakeLockDb()
        self.coordinator = DataTaskCoordinator(self.lock_db)

    def tearDown(self):
        active = self.coordinator.current()
        if active:
            self.coordinator.release(active['token'])

    def test_all_data_task_types_share_one_execution_slot(self):
        from app.services.data_task_coordinator import (
            DataTaskCoordinator,
            DataTaskBusyError,
            create_exclusive_background_task,
        )

        class FakeManager:
            def __init__(self):
                self.guarded = None

            def create_task(self, **kwargs):
                self.guarded = kwargs['func']
                return 'task-one'

        manager = FakeManager()
        with patch(
            'app.services.data_task_coordinator.get_data_task_coordinator',
            return_value=self.coordinator,
        ):
            first = create_exclusive_background_task(
                manager,
                task_type='stock_list_import',
                task_name='证券目录导入',
                func=lambda **_: {'success': True},
            )
            self.assertEqual(first, 'task-one')
            second_process = DataTaskCoordinator(self.lock_db)
            with patch(
                'app.services.data_task_coordinator.get_data_task_coordinator',
                return_value=second_process,
            ):
                with self.assertRaises(DataTaskBusyError):
                    create_exclusive_background_task(
                        manager,
                        task_type='data_update',
                        task_name='行情数据更新',
                        func=lambda **_: {'success': True},
                    )

            self.assertTrue(manager.guarded()['success'])
        self.assertIsNone(self.coordinator.current())

    def test_scheduled_task_is_logged_as_skipped_when_slot_is_busy(self):
        from app.scheduler.task_scheduler import TaskScheduler

        records = []

        class FakeDb:
            def insert_one(self, table, data):
                records.append((table, data))
                return 1

        token = self.coordinator.reserve(
            'data_import',
            '全量数据导入',
            'manual',
        )
        scheduler = TaskScheduler.__new__(TaskScheduler)
        scheduler.db = FakeDb()
        scheduler.market_data_service = type(
            'MarketData',
            (),
            {'incremental_update': lambda *args, **kwargs: self.fail(
                'busy 时不应执行行情更新'
            )},
        )()

        with patch(
            'app.scheduler.task_scheduler.get_data_task_coordinator',
            return_value=self.coordinator,
        ):
            result = scheduler._update_market_data_job()

        self.assertTrue(result['skipped'])
        self.assertEqual(records[0][0], 'job_logs')
        self.assertEqual(records[0][1]['status'], 'skipped')
        self.coordinator.release(token)

    def test_directory_job_writes_persistent_job_log(self):
        from app.services.data_task_jobs import execute_stock_list_import

        class FakeStocks:
            def fetch_and_save_stock_list(self):
                return {
                    'success': True,
                    'total': 12,
                    'success_count': 12,
                    'fail_count': 0,
                    'markets': {'CN': 4, 'HK': 4, 'US': 4},
                }

        class FakeScheduler:
            def __init__(self):
                self.success = None

            def _log_job_start(self, *args, **kwargs):
                return 88

            def _log_job_success(self, *args):
                self.success = args

            def _log_job_error(self, *args):
                raise AssertionError(args)

        scheduler = FakeScheduler()
        with (
            patch(
                'app.services.get_stock_service',
                return_value=FakeStocks(),
            ),
            patch(
                'app.scheduler.get_task_scheduler',
                return_value=scheduler,
            ),
        ):
            result = execute_stock_list_import()

        self.assertEqual(result['job_log_id'], 88)
        self.assertEqual(scheduler.success[-1], 88)


class MultiMarketBatchContractTests(unittest.TestCase):
    class FakeStockService:
        rows = {
            'CN': [
                {'id': 1, 'code': '600000', 'name': 'CN-1', 'security_type': 'STOCK'},
                {'id': 2, 'code': '510300', 'name': 'CN-2', 'security_type': 'ETF'},
            ],
            'HK': [
                {'id': 3, 'code': '00700', 'name': 'HK-1', 'security_type': 'STOCK'},
                {'id': 4, 'code': '02800', 'name': 'HK-2', 'security_type': 'ETF'},
            ],
            'US': [
                {'id': 5, 'code': 'AAPL', 'name': 'US-1', 'security_type': 'STOCK'},
                {'id': 6, 'code': 'QQQ', 'name': 'US-2', 'security_type': 'ETF'},
            ],
        }

        def get_stock_list(self, market_type=None):
            return [dict(row) for row in self.rows.get(market_type, [])]

    class NoopRateLimiter:
        def wait(self):
            return None

    class NoopDateRanges:
        def get_stock_date_range_from_daily_market(self, code, **kwargs):
            return None, None

        def needs_update(self, code, current_date, **kwargs):
            return True, '测试更新'

        def calculate_update_start_date(self, code, current_date, **kwargs):
            return current_date

    @staticmethod
    def build_service():
        from app.services.market_data_service import MarketDataService
        from app.utils import get_logger

        service = MarketDataService.__new__(MarketDataService)
        service.logger = get_logger('multi-market-contract-test')
        service.stock_service = (
            MultiMarketBatchContractTests.FakeStockService()
        )
        service.rate_limiter = (
            MultiMarketBatchContractTests.NoopRateLimiter()
        )
        service.date_range_service = (
            MultiMarketBatchContractTests.NoopDateRanges()
        )
        service._security_market_router = None
        service._delete_data_in_range = lambda *args: None
        service._save_daily_data = lambda *args, **kwargs: None
        return service

    def test_full_import_round_robins_all_markets(self):
        service = self.build_service()
        calls = []

        def fetch(security, start_date, end_date):
            calls.append((security['market'], security['code']))
            return pd.DataFrame([{
                'trade_date': start_date,
                'close': 1,
            }])

        service._fetch_security_daily_data = fetch
        result = service.import_all_history(
            start_date='2026-07-01',
            end_date='2026-07-25',
            limit=6,
            markets=['CN', 'HK', 'US'],
        )

        self.assertTrue(result['success'])
        self.assertEqual(
            calls,
            [
                ('CN', '600000'), ('HK', '00700'), ('US', 'AAPL'),
                ('CN', '510300'), ('HK', '02800'), ('US', 'QQQ'),
            ],
        )
        self.assertEqual(
            {
                market: stats['success']
                for market, stats in result['market_stats'].items()
            },
            {'CN': 2, 'HK': 2, 'US': 2},
        )

    def test_recent_and_scheduled_updates_cover_all_markets(self):
        service = self.build_service()
        recent_calls = []

        def fetch_recent(security, start_date, end_date):
            recent_calls.append(security['market'])
            return pd.DataFrame([{
                'trade_date': start_date,
                'close': 1,
            }])

        service._fetch_security_daily_data = fetch_recent
        recent = service.update_recent_data(
            days=3,
            only_existing=False,
            markets=['CN', 'HK', 'US'],
        )
        self.assertTrue(recent['success'])
        self.assertEqual(recent_calls[:3], ['CN', 'HK', 'US'])

        scheduled_calls = []

        def fetch_scheduled(security, start_date, end_date):
            scheduled_calls.append(security['market'])
            return pd.DataFrame([{
                'trade_date': start_date,
                'close': 1,
            }])

        service._fetch_security_daily_data = fetch_scheduled
        scheduled = service.incremental_update(
            markets=['CN', 'HK', 'US'],
        )
        self.assertTrue(scheduled['success'])
        self.assertEqual(scheduled_calls[:3], ['CN', 'HK', 'US'])

    def test_missing_market_fails_instead_of_silently_updating_cn(self):
        service = self.build_service()
        service.stock_service.rows = {
            **service.stock_service.rows,
            'US': [],
        }

        with self.assertRaisesRegex(ValueError, '缺少市场：US'):
            service.update_recent_data(
                markets=['CN', 'HK', 'US'],
            )

    def test_market_without_success_makes_batch_result_fail(self):
        service = self.build_service()

        def fetch(security, start_date, end_date):
            if security['market'] == 'US':
                return pd.DataFrame()
            return pd.DataFrame([{
                'trade_date': start_date,
                'close': 1,
            }])

        service._fetch_security_daily_data = fetch
        result = service.update_recent_data(
            markets=['CN', 'HK', 'US'],
        )

        self.assertFalse(result['success'])
        self.assertIn('US', result['market_errors'])
        self.assertGreater(result['market_stats']['CN']['success'], 0)
        self.assertGreater(result['market_stats']['HK']['success'], 0)
        self.assertEqual(result['market_stats']['US']['success'], 0)

    def test_background_task_respects_failed_service_result(self):
        from app.task_manager import BackgroundTask

        task = BackgroundTask(
            'task-market-failure',
            '跨市场行情更新',
            lambda **kwargs: {
                'success': False,
                'market_errors': {'US': '没有成功写入行情数据'},
            },
        )
        task._run_with_progress()

        self.assertEqual(task.status, 'failed')
        self.assertIn('US', task.error)

    def test_scheduler_explicitly_requests_all_markets(self):
        from app.scheduler.task_scheduler import TaskScheduler

        class FakeMarketData:
            def __init__(self):
                self.kwargs = None

            def incremental_update(self, **kwargs):
                self.kwargs = kwargs
                return {
                    'success': True,
                    'total_records': 3,
                    'markets': ['CN', 'HK', 'US'],
                    'market_stats': {},
                }

        service = FakeMarketData()
        scheduler = TaskScheduler.__new__(TaskScheduler)
        scheduler.market_data_service = service
        scheduler._log_job_start = lambda *args, **kwargs: 1
        scheduler._log_job_success = lambda *args, **kwargs: None
        scheduler._log_job_error = lambda *args, **kwargs: None

        coordinator = type(
            'Coordinator',
            (),
            {
                'reserve': lambda *args, **kwargs: 'token',
                'release': lambda *args, **kwargs: None,
            },
        )()
        with patch(
            'app.scheduler.task_scheduler.get_data_task_coordinator',
            return_value=coordinator,
        ):
            scheduler._update_market_data_job()

        self.assertEqual(
            service.kwargs,
            {'markets': ('CN', 'HK', 'US')},
        )


class StrategyContractTests(unittest.TestCase):
    def setUp(self):
        from app.api.routes.strategy_routes import strategy_bp

        self.app = make_api_app(strategy_bp, '/api/strategies')
        self.client = self.app.test_client()

    def test_missing_strategy_mutations_return_404(self):
        class MissingStrategy:
            def get_strategy(self, *args, **kwargs):
                return None

        with patch(
            'app.api.routes.strategy_routes.get_strategy_service',
            return_value=MissingStrategy(),
        ):
            responses = [
                self.client.put('/api/strategies/999999', json={'name': 'x'}),
                self.client.delete('/api/strategies/999999'),
                self.client.post('/api/strategies/999999/enable'),
                self.client.post('/api/strategies/999999/disable'),
            ]
        self.assertEqual([response.status_code for response in responses], [404] * 4)

    def test_invalid_strategy_fields_return_400(self):
        self.assertEqual(
            self.client.put('/api/strategies/1', json={}).status_code,
            400,
        )
        self.assertEqual(
            self.client.put(
                '/api/strategies/1',
                json={'unexpected': True},
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.get(
                '/api/strategies/1/results?limit=not-an-int'
            ).status_code,
            400,
        )

    def test_execute_strategy_creates_background_task(self):
        class FakeStrategy:
            def get_strategy(self, strategy_id, user_id=None):
                return {'id': strategy_id, 'name': '回归策略'}

        class FakeTasks:
            def __init__(self):
                self.call = None

            def create_task(self, **kwargs):
                self.call = kwargs
                return 'strategy-task'

        tasks = FakeTasks()
        with (
            patch(
                'app.api.routes.strategy_routes.get_strategy_service',
                return_value=FakeStrategy(),
            ),
            patch(
                'app.api.routes.strategy_routes.get_task_manager',
                return_value=tasks,
            ),
        ):
            response = self.client.post(
                '/api/strategies/1/execute',
                json={
                    'start_date': '2026-07-01',
                    'end_date': '2026-07-25',
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()['data']['task_id'],
            'strategy-task',
        )
        self.assertEqual(tasks.call['task_name'], '执行策略: 回归策略')


class SystemPageContractTests(unittest.TestCase):
    def test_system_pages_forward_browser_auth_cookie(self):
        from app.web.routes.system import system_bp

        template_dir = Path(__file__).resolve().parents[1] / 'app' / 'templates'
        app = Flask(
            __name__,
            template_folder=str(template_dir),
            static_folder=str(template_dir.parent / 'static'),
        )
        app.config['TESTING'] = True
        app.jinja_env.filters['datetime'] = lambda value: value
        app.register_blueprint(system_bp, url_prefix='/system')
        client = app.test_client()
        client.set_cookie('auth_token', 'browser-token')
        calls = []

        def fake_get(url, **kwargs):
            calls.append((url, kwargs))
            return FakeHttpResponse()

        with patch('app.web.routes.system.requests.get', side_effect=fake_get):
            self.assertEqual(client.get('/system/').status_code, 200)
            self.assertEqual(client.get('/system/logs').status_code, 200)
            self.assertEqual(client.get('/system/tasks').status_code, 200)

        self.assertGreaterEqual(len(calls), 7)
        for _, kwargs in calls:
            self.assertEqual(
                kwargs.get('headers'),
                {'Authorization': 'Bearer browser-token'},
            )

    def test_strategy_form_uses_backend_parameter_contract(self):
        from app.web.routes.strategy import strategy_bp

        template_dir = Path(__file__).resolve().parents[1] / 'app' / 'templates'
        app = Flask(
            __name__,
            template_folder=str(template_dir),
            static_folder=str(template_dir.parent / 'static'),
        )
        app.config['TESTING'] = True
        app.register_blueprint(strategy_bp, url_prefix='/strategies')
        client = app.test_client()
        html = client.get('/strategies/create').get_data(as_text=True)

        self.assertIn('max="30"', html)
        self.assertIn('<option value="60"', html)
        self.assertNotIn('max="365"', html)

    def test_ai_summary_uses_escaped_markdown_renderer(self):
        template = (
            Path(__file__).resolve().parents[1]
            / 'app'
            / 'templates'
            / 'reports.html'
        ).read_text(encoding='utf-8')

        self.assertIn('function renderSafeMarkdown(markdown)', template)
        self.assertIn('escapeHtml(value)', template)
        self.assertIn(
            "$('#ai-summary').html(renderSafeMarkdown(report.ai_summary))",
            template,
        )
        self.assertNotIn("$('#ai-summary').html(report.ai_summary)", template)

    def test_stock_page_forwards_industry_filter_to_api(self):
        from app.web.routes.stock import stock_bp

        template_dir = Path(__file__).resolve().parents[1] / 'app' / 'templates'
        app = Flask(
            __name__,
            template_folder=str(template_dir),
            static_folder=str(template_dir.parent / 'static'),
        )
        app.config['TESTING'] = True
        app.register_blueprint(stock_bp, url_prefix='/stocks')
        client = app.test_client()
        calls = []

        def fake_get(url, **kwargs):
            calls.append((url, kwargs))
            return FakeHttpResponse(payload={
                'success': True,
                'data': [],
                'pagination': {'total': 0},
            })

        with patch(
            'app.web.routes.stock.requests.get',
            side_effect=fake_get,
        ):
            response = client.get('/stocks/?industry=银行')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls[0][1]['params']['industry'], '银行')

    def test_data_page_explicitly_starts_cn_hk_us_tasks(self):
        template = (
            Path(__file__).resolve().parents[1]
            / 'app'
            / 'templates'
            / 'data'
            / 'index.html'
        ).read_text(encoding='utf-8')

        self.assertIn("markets: ['CN', 'HK', 'US']", template)
        self.assertIn('only_existing: false', template)
        self.assertIn('CN → HK → US', template)


class SystemMutationContractTests(unittest.TestCase):
    def setUp(self):
        from app.api.routes.system_routes import system_bp

        self.app = make_api_app(system_bp, '/api/system')
        self.client = self.app.test_client()

    def test_scheduler_mutations_dispatch_to_scheduler(self):
        class FakeInnerScheduler:
            running = True

        class FakeScheduler:
            def __init__(self):
                self.started = False
                self.stopped = False
                self.scheduler = FakeInnerScheduler()

            def run_job_now(self, job_id):
                return job_id == 'known'

            def start(self):
                self.started = True

            def shutdown(self, wait=False):
                self.stopped = not wait

        scheduler = FakeScheduler()
        with patch(
            'app.api.routes.system_routes.get_task_scheduler',
            return_value=scheduler,
        ):
            run = self.client.post('/api/system/scheduler/jobs/known/run')
            start = self.client.post('/api/system/scheduler/start')
            stop = self.client.post('/api/system/scheduler/stop')

        self.assertEqual([run.status_code, start.status_code, stop.status_code], [200] * 3)
        self.assertTrue(scheduler.started)
        self.assertTrue(scheduler.stopped)

    def test_config_update_handler_writes_allowed_existing_section(self):
        file_mock = mock_open(read_data='datasource:\n  type: akshare\n')

        class FakeConfig:
            def get(self, key, default=None):
                return default

        with (
            patch(
                'app.api.routes.system_routes.get_config',
                return_value=FakeConfig(),
            ),
            patch('builtins.open', file_mock),
        ):
            response = self.client.put(
                '/api/system/config',
                json={'datasource': {'type': 'tushare'}},
            )

        self.assertEqual(response.status_code, 200)
        file_mock.assert_any_call(
            str(Path(__file__).resolve().parents[1] / 'config.yaml'),
            'w',
            encoding='utf-8',
        )

    def test_database_status_falls_back_to_configured_type(self):
        class FakeDb:
            def execute_query(self, query):
                return [{'ok': 1}]

        class FakeMarketData:
            def get_data_statistics(self):
                return {'total_records': 0}

        class FakeConfig:
            def get(self, key, default=None):
                return 'mysql' if key == 'database.type' else default

        with (
            patch(
                'app.models.database_factory.get_database',
                return_value=FakeDb(),
            ),
            patch(
                'app.services.market_data_service.get_market_data_service',
                return_value=FakeMarketData(),
            ),
            patch(
                'app.api.routes.system_routes.get_config',
                return_value=FakeConfig(),
            ),
        ):
            response = self.client.get('/api/system/database-status')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()['data']['main_database']['type'],
            'mysql',
        )


class MCPToolContractTests(unittest.TestCase):
    class FakeMCP:
        def __init__(self):
            self.tools = {}

        def tool(self):
            def decorate(function):
                self.tools[function.__name__] = function
                return function
            return decorate

    def test_all_registered_tools_dispatch_for_authenticated_user(self):
        from app.mcp.server import current_user_id
        from app.mcp.tools.market_data_tools import register_market_data_tools
        from app.mcp.tools.watchlist_tools import register_watchlist_tools

        class FakeWatchlistService:
            def get_watchlist(self, user_id, group_name=None, tag=None):
                return [{'id': 3, 'stock_code': 'QQQ'}]

            def add_stock(self, **kwargs):
                return {'success': True, 'data': kwargs}

            def remove_stock(self, user_id, watchlist_id):
                return user_id == 7 and watchlist_id == 3

            def get_stock_data_with_indicators(self, **kwargs):
                return {
                    'stock_code': kwargs['stock_code'],
                    'market': kwargs['market'],
                    'currency': 'USD',
                    'records': [{'trade_date': '2026-07-25'}],
                    'summary': {'record_count': 1},
                    'indicators': {'ma_5': []},
                }

        mcp = self.FakeMCP()
        register_watchlist_tools(mcp)
        register_market_data_tools(mcp)
        self.assertEqual(set(mcp.tools), {
            'get_watchlist',
            'add_to_watchlist',
            'remove_from_watchlist',
            'get_stock_data',
            'get_stock_indicators',
        })

        context_token = current_user_id.set(7)
        try:
            with patch(
                'app.services.get_watchlist_service',
                return_value=FakeWatchlistService(),
            ):
                self.assertEqual(mcp.tools['get_watchlist']()['count'], 1)
                self.assertTrue(
                    mcp.tools['add_to_watchlist']('QQQ', 'US', 'ETF')['success']
                )
                self.assertTrue(mcp.tools['remove_from_watchlist'](3)['success'])
                self.assertEqual(
                    mcp.tools['get_stock_data']('QQQ', market='US')['currency'],
                    'USD',
                )
                self.assertIn(
                    'ma_5',
                    mcp.tools['get_stock_indicators'](
                        'QQQ',
                        market='US',
                        ma_periods='5',
                    )['indicators'],
                )
                self.assertIn(
                    'error',
                    mcp.tools['get_stock_indicators'](
                        'QQQ',
                        market='US',
                        ma_periods='bad',
                    ),
                )
        finally:
            current_user_id.reset(context_token)


if __name__ == '__main__':
    unittest.main()
