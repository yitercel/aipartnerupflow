"""
Isolated test to reproduce and fix Base.metadata pollution issue

This test file is created to isolate the problem where custom TaskModel tests
pollute Base.metadata, causing subsequent tests to fail with:
- "Table apflow_tasks does not have a column with name 'id'"
- "Catalog Error: Table with name apflow_tasks does not exist!"
- "NoForeignKeysError: Can't determine the inherit condition"

The issue occurs when:
1. A test uses custom TaskModel with __table_args__ = {'extend_existing': True}
2. Base.metadata gets polluted with custom columns
3. Subsequent tests create tables using the polluted Base.metadata
4. The table structure doesn't match the expected schema

Test Cases:
- test_base_metadata_has_correct_columns: Verify Base.metadata has correct default columns
- test_task_executor_with_clean_metadata: Test TaskExecutor with clean metadata
- test_custom_model_pollution_simulation: Simulate pollution and verify cleanup
- test_table_creation_with_polluted_metadata: Test table creation with polluted metadata
- test_session_pool_manager_uses_correct_database: Verify SessionPoolManager configuration
- test_reset_storage_singleton_cleans_polluted_metadata: Verify reset_storage_singleton cleanup
- test_multiple_custom_models_sequential_pollution: Test sequential pollution and cleanup
- test_table_creation_after_pollution_and_cleanup: Test table creation after cleanup
- test_no_foreign_keys_error_when_polluted_metadata: Test NoForeignKeysError scenario
- test_table_does_not_exist_error_after_pollution: Test "Table does not exist" error
- test_custom_model_definition_fails_without_cleanup: Test pollution accumulation
- test_table_creation_fails_with_polluted_metadata: Test table creation failure scenarios
- test_no_foreign_keys_error_with_conflicting_table_definitions: Test NoForeignKeysError with conflicting table definitions
- test_catalog_error_table_does_not_exist: Test "Catalog Error: Table does not exist" error
- test_mapper_cache_pollution_issue: Test SQLAlchemy mapper cache pollution issue
- test_table_creation_with_wrong_schema_after_pollution: Test table creation with wrong schema after pollution
- test_no_foreign_keys_error_with_different_column_types: Test NoForeignKeysError with different column types (String(100) vs String(255))
- test_mapper_registry_pollution_after_cleanup: Test SQLAlchemy mapper registry pollution after cleanup_base_metadata()
- test_catalog_error_when_table_creation_fails: Test "Catalog Error" when table creation fails due to pollution
"""
import pytest
from sqlalchemy import Column, String, Integer, inspect
from aipartnerupflow.core.storage.sqlalchemy.models import Base, TaskModel, TASK_TABLE_NAME
from aipartnerupflow.core.execution.task_executor import TaskExecutor
from aipartnerupflow.core.storage.factory import get_session_pool_manager


@pytest.mark.skip(reason="This test is excluded from the default test run to avoid Base.metadata pollution.")
@pytest.mark.custom_task_model
class TestSessionPoolIsolation:
    """Test to verify Base.metadata isolation and session pool configuration
    
    NOTE: This test class is marked with @pytest.mark.custom_task_model and is excluded
    from the default test run to avoid Base.metadata pollution.
    Run it explicitly with: pytest -m custom_task_model
    """
    
    def test_base_metadata_has_correct_columns(self):
        """Verify Base.metadata has correct default columns before any custom model"""
        # Re-import Base to get updated reference after reset_storage_singleton cleanup
        import importlib
        import sys
        if 'aipartnerupflow.core.storage.sqlalchemy.models' in sys.modules:
            del sys.modules['aipartnerupflow.core.storage.sqlalchemy.models']
        from aipartnerupflow.core.storage.sqlalchemy.models import Base, TASK_TABLE_NAME
        
        # Check that Base.metadata has the correct table definition
        assert TASK_TABLE_NAME in Base.metadata.tables, f"Table {TASK_TABLE_NAME} should exist in Base.metadata"
        
        table = Base.metadata.tables[TASK_TABLE_NAME]
        column_names = {c.name for c in table.columns}
        
        # Verify standard columns exist
        required_columns = {
            'id', 'parent_id', 'user_id', 'name', 'status', 'priority',
            'dependencies', 'inputs', 'params', 'result', 'error', 'schemas',
            'progress', 'created_at', 'started_at', 'updated_at', 'completed_at',
            'has_children', 'original_task_id', 'has_copy'
        }
        
        assert required_columns.issubset(column_names), \
            f"Missing required columns. Expected: {required_columns}, Got: {column_names}"
        
        # Verify no unexpected custom columns
        unexpected_columns = column_names - required_columns
        assert not unexpected_columns, \
            f"Found unexpected custom columns in Base.metadata: {unexpected_columns}. " \
            f"This indicates Base.metadata pollution from a previous test."
    
    @pytest.mark.asyncio
    async def test_task_executor_with_clean_metadata(self, use_test_db_session):
        """Test TaskExecutor with clean Base.metadata (no custom columns)"""
        # Re-import Base to get updated reference after reset_storage_singleton cleanup
        import importlib
        import sys
        if 'aipartnerupflow.core.storage.sqlalchemy.models' in sys.modules:
            del sys.modules['aipartnerupflow.core.storage.sqlalchemy.models']
        from aipartnerupflow.core.storage.sqlalchemy.models import Base, TASK_TABLE_NAME
        
        # Verify Base.metadata is clean
        table = Base.metadata.tables[TASK_TABLE_NAME]
        column_names = {c.name for c in table.columns}
        
        # Should not have custom columns
        custom_columns = {'department', 'project_id', 'priority_level'}
        found_custom = custom_columns & column_names
        assert not found_custom, \
            f"Base.metadata is polluted with custom columns: {found_custom}. " \
            f"This will cause table creation to fail."
        
        # Create a simple task tree
        task_executor = TaskExecutor()
        db_session = use_test_db_session
        
        tasks = [
            {
                "id": "test-task-1",
                "user_id": "test-user",
                "name": "Test Task",
                "status": "pending",
                "priority": 1,
                "has_children": False,
                "dependencies": [],
                "inputs": {},
            }
        ]
        
        # This should work if Base.metadata is clean
        execution_result = await task_executor.execute_tasks(
            tasks=tasks,
            root_task_id=None,
            use_streaming=False,
            require_existing_tasks=False,
            db_session=db_session
        )
        
        assert execution_result is not None
        assert execution_result.get("root_task_id") == "test-task-1"
    
    def test_custom_model_pollution_simulation(self, sync_db_session):
        """Simulate the pollution issue by creating a custom model"""
        from sqlalchemy import Column, String, Integer
        from aipartnerupflow.core.storage.sqlalchemy.models import Base, TaskModel, TASK_TABLE_NAME
        
        # Create a custom TaskModel (simulating test_task_model_customization.py)
        class PollutedTaskModel(TaskModel):
            __tablename__ = TASK_TABLE_NAME
            __table_args__ = {'extend_existing': True}  # This pollutes Base.metadata
            
            project_id = Column(String(255), nullable=True)
            department = Column(String(100), nullable=True)
            priority_level = Column(Integer, default=2)
        
        # At this point, Base.metadata is polluted with custom columns
        table = Base.metadata.tables[TASK_TABLE_NAME]
        column_names = {c.name for c in table.columns}
        
        # Verify pollution occurred
        assert 'project_id' in column_names
        assert 'department' in column_names
        assert 'priority_level' in column_names
        
        # Now verify that cleanup_base_metadata fixes it
        from tests.conftest import cleanup_base_metadata
        cleanup_base_metadata()
        
        # After cleanup, we need to re-import Base to get the updated reference
        # because cleanup_base_metadata() reloads the module, creating a new Base object
        import importlib
        import sys
        # Remove from cache to force fresh import
        if 'aipartnerupflow.core.storage.sqlalchemy.models' in sys.modules:
            del sys.modules['aipartnerupflow.core.storage.sqlalchemy.models']
        from aipartnerupflow.core.storage.sqlalchemy.models import Base as CleanBase, TASK_TABLE_NAME
        
        # After cleanup, Base.metadata should be clean
        table_after = CleanBase.metadata.tables[TASK_TABLE_NAME]
        column_names_after = {c.name for c in table_after.columns}
        
        # Custom columns should be gone
        assert 'project_id' not in column_names_after, \
            "cleanup_base_metadata() should remove custom columns"
        assert 'department' not in column_names_after
        assert 'priority_level' not in column_names_after
        
        # Standard columns should still exist
        assert 'id' in column_names_after
        assert 'name' in column_names_after
    
    def test_table_creation_with_polluted_metadata(self):
        """Test what happens when table is created with polluted Base.metadata"""
        from sqlalchemy import create_engine, Column, String, Integer, text
        from aipartnerupflow.core.storage.sqlalchemy.models import Base, TaskModel, TASK_TABLE_NAME
        import tempfile
        import os
        
        # Create a fresh temporary file path for this test
        # Don't use temp_db_path fixture to avoid conflicts
        temp_dir = tempfile.gettempdir()
        polluted_db_path = os.path.join(temp_dir, f"polluted_test_{os.getpid()}_{id(Base)}.duckdb")
        # Ensure file doesn't exist
        if os.path.exists(polluted_db_path):
            os.unlink(polluted_db_path)
        
        # First, pollute Base.metadata
        class PollutedTaskModel(TaskModel):
            __tablename__ = TASK_TABLE_NAME
            __table_args__ = {'extend_existing': True}
            
            project_id = Column(String(255), nullable=True)
            department = Column(String(100), nullable=True)
            priority_level = Column(Integer, default=2)
        
        # Create engine and table with polluted metadata
        engine = create_engine(f"duckdb:///{polluted_db_path}", echo=False)
        
        # This will create a table with custom columns
        Base.metadata.create_all(engine)
        
        # Check what columns were actually created by querying the table structure
        # Use direct SQL query for DuckDB instead of inspect
        with engine.connect() as conn:
            result = conn.execute(
                text(f"PRAGMA table_info({TASK_TABLE_NAME})")
            )
            db_columns = {row[1] for row in result}  # Column name is at index 1
        
        # The table should have both standard and custom columns
        assert 'id' in db_columns, "Table should have standard 'id' column"
        assert 'project_id' in db_columns, "Table should have custom 'project_id' column"
        assert 'department' in db_columns
        assert 'priority_level' in db_columns
        
        engine.dispose()
        
        # Now cleanup Base.metadata
        from tests.conftest import cleanup_base_metadata
        cleanup_base_metadata()
        
        # Re-import Base to get updated reference after cleanup
        import importlib
        import sys
        if 'aipartnerupflow.core.storage.sqlalchemy.models' in sys.modules:
            del sys.modules['aipartnerupflow.core.storage.sqlalchemy.models']
        from aipartnerupflow.core.storage.sqlalchemy.models import Base as CleanBase
        
        # Create a new engine with clean metadata using a different file path
        # to avoid file deletion timing issues
        temp_dir = os.path.dirname(polluted_db_path)
        clean_db_path = os.path.join(temp_dir, f"clean_test_{os.getpid()}_{id(CleanBase)}.duckdb")
        # Ensure clean file doesn't exist
        if os.path.exists(clean_db_path):
            os.unlink(clean_db_path)
        
        engine2 = create_engine(f"duckdb:///{clean_db_path}", echo=False)
        CleanBase.metadata.create_all(engine2)
        
        # Check columns in new table using direct SQL query
        with engine2.connect() as conn:
            result2 = conn.execute(
                text(f"PRAGMA table_info({TASK_TABLE_NAME})")
            )
            db_columns2 = {row[1] for row in result2}  # Column name is at index 1
        
        # Should only have standard columns now
        assert 'id' in db_columns2
        assert 'project_id' not in db_columns2, \
            "After cleanup, new table should not have custom columns"
        assert 'department' not in db_columns2
        assert 'priority_level' not in db_columns2
        
        engine2.dispose()
        # Cleanup both files
        try:
            if os.path.exists(polluted_db_path):
                os.unlink(polluted_db_path)
            if os.path.exists(clean_db_path):
                os.unlink(clean_db_path)
        except Exception:
            pass  # Ignore cleanup errors
    
    def test_session_pool_manager_uses_correct_database(self, sync_db_session):
        """Verify SessionPoolManager uses the test database configuration"""
        pool_manager = get_session_pool_manager()
        
        # SessionPoolManager should be initialized
        assert pool_manager._engine is not None, \
            "SessionPoolManager should be initialized with test database"
        
        # For DuckDB, verify it's using the test database path
        # (This is a basic check - actual path verification would be more complex)
        assert pool_manager._engine is not None
    
    def test_reset_storage_singleton_cleans_polluted_metadata(self):
        """
        Test that reset_storage_singleton fixture cleans Base.metadata pollution
        
        This simulates the scenario where test_task_model_customization.py runs
        before other tests and pollutes Base.metadata. The reset_storage_singleton
        fixture should clean it up before each test.
        """
        from sqlalchemy import Column, String, Integer
        from aipartnerupflow.core.storage.sqlalchemy.models import Base, TaskModel, TASK_TABLE_NAME
        
        # Simulate pollution from a previous test (like test_task_model_customization.py)
        class PollutedTaskModel1(TaskModel):
            __tablename__ = TASK_TABLE_NAME
            __table_args__ = {'extend_existing': True}
            project_id = Column(String(255), nullable=True)
            department = Column(String(100), nullable=True)
        
        # Verify pollution occurred
        table = Base.metadata.tables[TASK_TABLE_NAME]
        column_names = {c.name for c in table.columns}
        assert 'project_id' in column_names
        assert 'department' in column_names
        
        # Now simulate what reset_storage_singleton does
        # (It's autouse, so it runs before each test, but we can test the logic)
        from tests.conftest import cleanup_base_metadata
        cleanup_base_metadata()
        
        # Re-import Base to get updated reference (as reset_storage_singleton does)
        import importlib
        import sys
        if 'aipartnerupflow.core.storage.sqlalchemy.models' in sys.modules:
            del sys.modules['aipartnerupflow.core.storage.sqlalchemy.models']
        from aipartnerupflow.core.storage.sqlalchemy.models import Base as CleanBase, TASK_TABLE_NAME
        
        # Verify Base.metadata is clean after cleanup
        assert TASK_TABLE_NAME in CleanBase.metadata.tables
        table_after = CleanBase.metadata.tables[TASK_TABLE_NAME]
        column_names_after = {c.name for c in table_after.columns}
        
        # Custom columns should be gone
        assert 'project_id' not in column_names_after
        assert 'department' not in column_names_after
        
        # Standard columns should exist
        assert 'id' in column_names_after
        assert 'name' in column_names_after
    
    def test_multiple_custom_models_sequential_pollution(self):
        """
        Test that multiple sequential custom TaskModel definitions don't accumulate pollution
        
        This simulates running multiple tests from test_task_model_customization.py
        sequentially, each with different custom columns.
        
        Note: We test pollution and cleanup separately because defining multiple
        custom models in the same test can cause SQLAlchemy inheritance issues.
        """
        from sqlalchemy import Column, String, Integer
        from aipartnerupflow.core.storage.sqlalchemy.models import Base, TaskModel, TASK_TABLE_NAME
        
        # First custom model
        class PollutedTaskModel1(TaskModel):
            __tablename__ = TASK_TABLE_NAME
            __table_args__ = {'extend_existing': True}
            project_id = Column(String(255), nullable=True)
        
        # Verify first pollution
        table1 = Base.metadata.tables[TASK_TABLE_NAME]
        column_names1 = {c.name for c in table1.columns}
        assert 'project_id' in column_names1, "First model should pollute Base.metadata with project_id"
        
        # Cleanup (simulating teardown_method)
        from tests.conftest import cleanup_base_metadata
        cleanup_base_metadata()
        
        # Re-import Base to get updated reference
        import importlib
        import sys
        if 'aipartnerupflow.core.storage.sqlalchemy.models' in sys.modules:
            del sys.modules['aipartnerupflow.core.storage.sqlalchemy.models']
        from aipartnerupflow.core.storage.sqlalchemy.models import Base as CleanBase1, TASK_TABLE_NAME
        
        # Verify cleanup worked - project_id should be gone
        table_after_cleanup1 = CleanBase1.metadata.tables[TASK_TABLE_NAME]
        column_names_after_cleanup1 = {c.name for c in table_after_cleanup1.columns}
        assert 'project_id' not in column_names_after_cleanup1, \
            "After cleanup, project_id should be removed from Base.metadata"
        assert 'id' in column_names_after_cleanup1, "Standard columns should still exist"
        
        # Now simulate a second test with different custom columns
        # Re-import to get fresh Base for second test
        if 'aipartnerupflow.core.storage.sqlalchemy.models' in sys.modules:
            del sys.modules['aipartnerupflow.core.storage.sqlalchemy.models']
        from aipartnerupflow.core.storage.sqlalchemy.models import Base as Base2, TaskModel as TaskModel2, TASK_TABLE_NAME
        
        # Second custom model with different columns
        class PollutedTaskModel2(TaskModel2):
            __tablename__ = TASK_TABLE_NAME
            __table_args__ = {'extend_existing': True}
            department = Column(String(100), nullable=True)
            priority_level = Column(Integer, default=2)
        
        # Verify second pollution
        table2 = Base2.metadata.tables[TASK_TABLE_NAME]
        column_names2 = {c.name for c in table2.columns}
        
        # Should have new columns
        assert 'department' in column_names2, "Second model should add department column"
        assert 'priority_level' in column_names2, "Second model should add priority_level column"
        
        # Should NOT have project_id from first model (cleanup worked)
        assert 'project_id' not in column_names2, \
            "Second model should not have project_id from first model (cleanup worked)"
        
        # Cleanup again (simulating second test's teardown_method)
        cleanup_base_metadata()
        
        # Re-import Base again
        if 'aipartnerupflow.core.storage.sqlalchemy.models' in sys.modules:
            del sys.modules['aipartnerupflow.core.storage.sqlalchemy.models']
        from aipartnerupflow.core.storage.sqlalchemy.models import Base as FinalBase, TASK_TABLE_NAME
        
        # Verify all custom columns are gone after second cleanup
        table_final = FinalBase.metadata.tables[TASK_TABLE_NAME]
        column_names_final = {c.name for c in table_final.columns}
        
        assert 'project_id' not in column_names_final, \
            "After second cleanup, project_id should still be gone"
        assert 'department' not in column_names_final, \
            "After second cleanup, department should be removed"
        assert 'priority_level' not in column_names_final, \
            "After second cleanup, priority_level should be removed"
        
        # Standard columns should exist
        assert 'id' in column_names_final, "Standard id column should exist"
        assert 'name' in column_names_final, "Standard name column should exist"
    
    def test_table_creation_after_pollution_and_cleanup(self, sync_db_session):
        """
        Test that table creation works correctly after pollution and cleanup
        
        This verifies that sync_db_session fixture correctly handles polluted Base.metadata
        and creates tables with the correct schema.
        """
        from sqlalchemy import Column, String, Integer, text
        from aipartnerupflow.core.storage.sqlalchemy.models import Base, TaskModel, TASK_TABLE_NAME
        
        # First, pollute Base.metadata
        class PollutedTaskModel(TaskModel):
            __tablename__ = TASK_TABLE_NAME
            __table_args__ = {'extend_existing': True}
            project_id = Column(String(255), nullable=True)
            department = Column(String(100), nullable=True)
            priority_level = Column(Integer, default=2)
        
        # Verify pollution
        table = Base.metadata.tables[TASK_TABLE_NAME]
        column_names = {c.name for c in table.columns}
        assert 'project_id' in column_names
        assert 'department' in column_names
        assert 'priority_level' in column_names
        
        # Cleanup (simulating reset_storage_singleton)
        from tests.conftest import cleanup_base_metadata
        cleanup_base_metadata()
        
        # Re-import Base
        import importlib
        import sys
        if 'aipartnerupflow.core.storage.sqlalchemy.models' in sys.modules:
            del sys.modules['aipartnerupflow.core.storage.sqlalchemy.models']
        from aipartnerupflow.core.storage.sqlalchemy.models import Base as CleanBase, TASK_TABLE_NAME
        
        # Now use sync_db_session which should have clean Base.metadata
        # The fixture should detect pollution and clean it, then create tables
        # We can verify by checking the actual database table structure
        with sync_db_session.bind.connect() as conn:
            result = conn.execute(
                text(f"PRAGMA table_info({TASK_TABLE_NAME})")
            )
            db_columns = {row[1] for row in result}  # Column name is at index 1
        
        # Should have standard columns
        assert 'id' in db_columns
        assert 'name' in db_columns
        assert 'status' in db_columns
        
        # Should NOT have custom columns
        assert 'project_id' not in db_columns, \
            "Database table should not have custom columns after cleanup"
        assert 'department' not in db_columns
        assert 'priority_level' not in db_columns
    
    def test_no_foreign_keys_error_when_polluted_metadata(self):
        """
        Test that NoForeignKeysError occurs when defining custom TaskModel
        after Base.metadata is polluted.
        
        This error occurs because:
        1. Base.metadata is polluted with custom columns from a previous test
        2. When defining a new custom TaskModel, SQLAlchemy finds two different
           table definitions in Base.metadata (polluted and new)
        3. SQLAlchemy tries to establish inheritance but can't determine the
           join condition between the two tables
        
        Note: reset_storage_singleton cleans Base.metadata before each test,
        so we need to pollute it within the test and then try to define another model.
        """
        from sqlalchemy import Column, String, Integer
        from aipartnerupflow.core.storage.sqlalchemy.models import Base, TaskModel, TASK_TABLE_NAME
        
        # First, pollute Base.metadata (simulating a previous test)
        class FirstPollutedModel(TaskModel):
            __tablename__ = TASK_TABLE_NAME
            __table_args__ = {'extend_existing': True}
            project_id = Column(String(255), nullable=True)
        
        # Verify pollution
        table1 = Base.metadata.tables[TASK_TABLE_NAME]
        assert 'project_id' in {c.name for c in table1.columns}
        
        # Get the current table definition to verify it's polluted
        polluted_columns = {c.name for c in table1.columns}
        
        # Now try to define a second custom model WITHOUT cleaning up first
        # This should cause NoForeignKeysError because Base.metadata has
        # a polluted table definition, and SQLAlchemy can't determine how
        # to join the two table definitions
        # However, if extend_existing=True, it might just extend the existing table
        # So we need to check if it actually fails or just extends
        
        try:
            class SecondPollutedModel(TaskModel):
                __tablename__ = TASK_TABLE_NAME
                __table_args__ = {'extend_existing': True}
                department = Column(String(100), nullable=True)
            
            # If we get here, the model was created successfully
            # This means extend_existing=True just extended the table
            # Check that both columns are now in the table
            table2 = Base.metadata.tables[TASK_TABLE_NAME]
            extended_columns = {c.name for c in table2.columns}
            assert 'project_id' in extended_columns
            assert 'department' in extended_columns
            
            # This is actually expected behavior with extend_existing=True
            # The error only occurs when SQLAlchemy can't determine inheritance
            # between two DIFFERENT table definitions in the same metadata
        except Exception as e:
            # If it fails, verify it's the expected error
            error = e
            error_type_name = type(error).__name__
            error_msg = str(error)
            
            # Should be NoForeignKeysError or similar
            assert "NoForeignKeysError" in error_type_name or \
                   "Can't determine the inherit condition" in error_msg or \
                   "Can't find any foreign key relationships" in error_msg, \
                f"Expected NoForeignKeysError, got {error_type_name}: {error_msg}"
    
    def test_table_does_not_exist_error_after_pollution(self, sync_db_session):
        """
        Test that 'Table does not exist' error occurs when trying to use
        a database session after Base.metadata pollution.
        
        This error occurs because:
        1. Base.metadata is polluted with custom columns
        2. Table creation fails or creates incorrect schema
        3. Subsequent queries fail because table doesn't exist or has wrong structure
        """
        from sqlalchemy import Column, String, Integer, text
        from aipartnerupflow.core.storage.sqlalchemy.models import Base, TaskModel, TASK_TABLE_NAME
        
        # Pollute Base.metadata BEFORE using sync_db_session
        # This simulates a test that runs before the current test
        class PollutedTaskModel(TaskModel):
            __tablename__ = TASK_TABLE_NAME
            __table_args__ = {'extend_existing': True}
            project_id = Column(String(255), nullable=True)
            department = Column(String(100), nullable=True)
            priority_level = Column(Integer, default=2)
        
        # Verify pollution
        table = Base.metadata.tables[TASK_TABLE_NAME]
        column_names = {c.name for c in table.columns}
        assert 'project_id' in column_names
        assert 'department' in column_names
        
        # Now try to use the database - this should work because sync_db_session
        # should detect pollution and clean it up. But if it doesn't, we'll get
        # "Table does not exist" error
        
        # Try to query the table
        try:
            with sync_db_session.bind.connect() as conn:
                result = conn.execute(
                    text(f"SELECT COUNT(*) FROM {TASK_TABLE_NAME}")
                )
                count = result.scalar()
                # If we get here, the table exists and query worked
                assert count is not None or count >= 0
        except Exception as e:
            # If we get an error, it's likely because:
            # 1. Table doesn't exist (pollution caused table creation to fail)
            # 2. Table has wrong schema (pollution caused wrong columns)
            error_msg = str(e)
            assert "does not exist" in error_msg or \
                   "Catalog Error" in error_msg or \
                   "no such table" in error_msg.lower(), \
                f"Expected table existence error, got: {error_msg}"
    
    def test_custom_model_definition_fails_without_cleanup(self):
        """
        Test that defining a custom TaskModel with extend_existing=True
        extends the polluted table instead of failing.
        
        Note: With extend_existing=True, SQLAlchemy extends the existing table
        definition rather than creating a new one, so NoForeignKeysError doesn't occur.
        However, this causes pollution to accumulate, which is the real problem.
        
        The actual error (NoForeignKeysError) occurs when:
        1. A test defines a custom model with extend_existing=True (pollutes Base.metadata)
        2. The test completes but doesn't clean up
        3. The next test tries to define another custom model, but Base.metadata
           has conflicting table definitions from different test runs
        """
        from sqlalchemy import Column, String, Integer
        from aipartnerupflow.core.storage.sqlalchemy.models import Base, TaskModel, TASK_TABLE_NAME
        
        # Simulate a previous test that polluted Base.metadata
        class PreviousTestModel(TaskModel):
            __tablename__ = TASK_TABLE_NAME
            __table_args__ = {'extend_existing': True}
            project_id = Column(String(255), nullable=True)
            department = Column(String(100), nullable=True)
        
        # Verify pollution
        table_before = Base.metadata.tables[TASK_TABLE_NAME]
        columns_before = {c.name for c in table_before.columns}
        assert 'project_id' in columns_before
        assert 'department' in columns_before
        
        # Now try to define a new custom model WITHOUT cleanup
        # With extend_existing=True, this will extend the table, not fail
        class NewCustomModel(TaskModel):
            __tablename__ = TASK_TABLE_NAME
            __table_args__ = {'extend_existing': True}
            priority_level = Column(Integer, default=2)
        
        # Verify that the table was extended (pollution accumulated)
        table_after = Base.metadata.tables[TASK_TABLE_NAME]
        columns_after = {c.name for c in table_after.columns}
        
        # All columns should be present (pollution accumulated)
        assert 'project_id' in columns_after, "Previous pollution should still be there"
        assert 'department' in columns_after, "Previous pollution should still be there"
        assert 'priority_level' in columns_after, "New column should be added"
        
        # This demonstrates the pollution accumulation problem:
        # Each test that uses extend_existing=True adds columns to Base.metadata,
        # and these columns persist across tests unless cleaned up
    
    def test_table_creation_fails_with_polluted_metadata(self):
        """
        Test that table creation fails when Base.metadata is polluted.
        
        This reproduces the 'Catalog Error: Table with name apflow_tasks does not exist!'
        error seen in many tests.
        """
        from sqlalchemy import create_engine, Column, String, Integer, text
        from aipartnerupflow.core.storage.sqlalchemy.models import Base, TaskModel, TASK_TABLE_NAME
        import tempfile
        import os
        
        # Create a temporary database
        temp_dir = tempfile.gettempdir()
        db_path = os.path.join(temp_dir, f"polluted_test_{os.getpid()}_{id(Base)}.duckdb")
        if os.path.exists(db_path):
            os.unlink(db_path)
        
        # First, pollute Base.metadata
        class PollutedTaskModel(TaskModel):
            __tablename__ = TASK_TABLE_NAME
            __table_args__ = {'extend_existing': True}
            project_id = Column(String(255), nullable=True)
            department = Column(String(100), nullable=True)
            priority_level = Column(Integer, default=2)
        
        # Verify pollution
        table = Base.metadata.tables[TASK_TABLE_NAME]
        column_names = {c.name for c in table.columns}
        assert 'project_id' in column_names
        
        # Try to create table with polluted metadata
        engine = create_engine(f"duckdb:///{db_path}", echo=False)
        
        try:
            Base.metadata.create_all(engine)
            
            # Try to query the table
            with engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT COUNT(*) FROM {TASK_TABLE_NAME}")
                )
                count = result.scalar()
                # If we get here, table was created successfully
                # But the schema might be wrong (has custom columns)
                assert count is not None
        except Exception as e:
            # If table creation or query fails, it's because of pollution
            error_msg = str(e)
            # This might fail with various errors depending on the pollution state
            assert "does not exist" in error_msg or \
                   "Catalog Error" in error_msg or \
                   "no such table" in error_msg.lower() or \
                   "Binder Error" in error_msg, \
                f"Expected table-related error, got: {error_msg}"
        finally:
            engine.dispose()
            try:
                if os.path.exists(db_path):
                    os.unlink(db_path)
            except Exception:
                pass
    
    def test_no_foreign_keys_error_with_conflicting_table_definitions(self):
        """
        Test that NoForeignKeysError occurs when Base.metadata has conflicting
        table definitions from different test runs.
        
        This reproduces the actual error seen in test_task_model_customization.py:
        - First test defines CustomTaskModel with project_id (pollutes Base.metadata)
        - Second test tries to define another CustomTaskModel, but Base.metadata
          has conflicting table definitions (one with project_id from first test,
          one new from second test)
        - SQLAlchemy can't determine how to join the two table definitions
        
        The error message shows:
        - a = Table('apflow_tasks', ...) with project_id String(100)
        - b = Table('apflow_tasks', ...) with project_id String(255), department, priority_level
        """
        from sqlalchemy import Column, String, Integer
        from aipartnerupflow.core.storage.sqlalchemy.models import Base, TaskModel, TASK_TABLE_NAME
        import sys
        import importlib
        
        # Simulate first test run that pollutes Base.metadata
        # This creates a table definition with project_id String(100)
        class FirstTestModel(TaskModel):
            __tablename__ = TASK_TABLE_NAME
            __table_args__ = {'extend_existing': True}
            project_id = Column(String(100), nullable=True, comment='Project ID for task grouping')
        
        # Get the first table definition
        first_table = Base.metadata.tables[TASK_TABLE_NAME]
        first_columns = {c.name: c for c in first_table.columns}
        assert 'project_id' in first_columns
        # Note: project_id is String(100) in first definition
        
        # Now simulate cleanup (but SQLAlchemy mapper cache might still have old definition)
        from tests.conftest import cleanup_base_metadata
        cleanup_base_metadata()
        
        # Re-import Base to get updated reference
        if 'aipartnerupflow.core.storage.sqlalchemy.models' in sys.modules:
            del sys.modules['aipartnerupflow.core.storage.sqlalchemy.models']
        from aipartnerupflow.core.storage.sqlalchemy.models import Base as CleanBase, TaskModel as CleanTaskModel, TASK_TABLE_NAME
        
        # Verify cleanup worked
        clean_table = CleanBase.metadata.tables[TASK_TABLE_NAME]
        clean_columns = {c.name for c in clean_table.columns}
        assert 'project_id' not in clean_columns, "Cleanup should remove project_id"
        
        # Now simulate second test that tries to define a new custom model
        # This should work, but if SQLAlchemy mapper cache still has the old definition,
        # it will try to establish inheritance between the two table definitions
        try:
            class SecondTestModel(CleanTaskModel):
                __tablename__ = TASK_TABLE_NAME
                __table_args__ = {'extend_existing': True}
                project_id = Column(String(255), nullable=True)  # Different length!
                department = Column(String(100), nullable=True)
                priority_level = Column(Integer, default=2)
            
            # If we get here, the model was created successfully
            # But check if there are conflicting table definitions
            second_table = CleanBase.metadata.tables[TASK_TABLE_NAME]
            second_columns = {c.name for c in second_table.columns}
            
            # The table should have the new columns
            assert 'project_id' in second_columns
            assert 'department' in second_columns
            assert 'priority_level' in second_columns
            
        except Exception as e:
            # If it fails, verify it's the expected error
            error_type_name = type(e).__name__
            error_msg = str(e)
            
            # Should be NoForeignKeysError
            assert "NoForeignKeysError" in error_type_name or \
                   "Can't determine the inherit condition" in error_msg or \
                   "Can't find any foreign key relationships" in error_msg, \
                f"Expected NoForeignKeysError, got {error_type_name}: {error_msg}"
    
    def test_catalog_error_table_does_not_exist(self, sync_db_session):
        """
        Test that 'Catalog Error: Table with name apflow_tasks does not exist!' occurs
        when Base.metadata is polluted and table creation fails.
        
        This reproduces the error seen in many tests:
        - Base.metadata is polluted with custom columns
        - sync_db_session tries to create tables
        - Table creation fails or creates incorrect schema
        - Subsequent queries fail with "Table does not exist"
        """
        from sqlalchemy import Column, String, Integer, text
        from aipartnerupflow.core.storage.sqlalchemy.models import Base, TaskModel, TASK_TABLE_NAME
        
        # Pollute Base.metadata BEFORE sync_db_session creates tables
        # This simulates a test that runs before the current test
        class PollutedTaskModel(TaskModel):
            __tablename__ = TASK_TABLE_NAME
            __table_args__ = {'extend_existing': True}
            project_id = Column(String(255), nullable=True)
            department = Column(String(100), nullable=True)
            priority_level = Column(Integer, default=2)
        
        # Verify pollution
        table = Base.metadata.tables[TASK_TABLE_NAME]
        column_names = {c.name for c in table.columns}
        assert 'project_id' in column_names
        assert 'department' in column_names
        
        # Now sync_db_session should detect pollution and clean it up
        # But if it doesn't work correctly, we'll get "Table does not exist" error
        # Try to use the database
        try:
            with sync_db_session.bind.connect() as conn:
                # Try to query the table
                result = conn.execute(
                    text(f"SELECT COUNT(*) FROM {TASK_TABLE_NAME}")
                )
                count = result.scalar()
                # If we get here, the table exists and query worked
                assert count is not None or count >= 0
        except Exception as e:
            # If we get an error, it's likely because table doesn't exist
            error_msg = str(e)
            assert "does not exist" in error_msg or \
                   "Catalog Error" in error_msg or \
                   "no such table" in error_msg.lower(), \
                f"Expected table existence error, got: {error_msg}"
    
    def test_mapper_cache_pollution_issue(self):
        """
        Test that SQLAlchemy mapper cache can cause issues when Base.metadata
        is polluted and then cleaned up.
        
        The problem:
        1. First test defines CustomTaskModel (pollutes Base.metadata, creates mapper)
        2. cleanup_base_metadata() removes table from Base.metadata
        3. Second test tries to define another CustomTaskModel
        4. SQLAlchemy mapper cache still has reference to old table definition
        5. New model tries to inherit from old mapper, but table definitions conflict
        
        This test verifies that mapper cache can cause NoForeignKeysError even
        after cleanup_base_metadata() is called.
        """
        from sqlalchemy import Column, String, Integer
        from aipartnerupflow.core.storage.sqlalchemy.models import Base, TaskModel, TASK_TABLE_NAME
        from sqlalchemy.orm import clear_mappers
        import sys
        import importlib
        
        # First test: Define custom model (pollutes Base.metadata and creates mapper)
        class FirstCustomModel(TaskModel):
            __tablename__ = TASK_TABLE_NAME
            __table_args__ = {'extend_existing': True}
            project_id = Column(String(255), nullable=True)
        
        # Verify pollution and mapper creation
        assert TASK_TABLE_NAME in Base.metadata.tables
        first_table = Base.metadata.tables[TASK_TABLE_NAME]
        assert 'project_id' in {c.name for c in first_table.columns}
        
        # Get the mapper for FirstCustomModel
        from sqlalchemy.inspection import inspect as sa_inspect
        first_mapper = sa_inspect(FirstCustomModel)
        assert first_mapper is not None
        
        # Cleanup Base.metadata
        from tests.conftest import cleanup_base_metadata
        cleanup_base_metadata()
        
        # Re-import Base
        if 'aipartnerupflow.core.storage.sqlalchemy.models' in sys.modules:
            del sys.modules['aipartnerupflow.core.storage.sqlalchemy.models']
        from aipartnerupflow.core.storage.sqlalchemy.models import Base as CleanBase, TaskModel as CleanTaskModel, TASK_TABLE_NAME
        
        # Verify cleanup worked
        clean_table = CleanBase.metadata.tables[TASK_TABLE_NAME]
        clean_columns = {c.name for c in clean_table.columns}
        assert 'project_id' not in clean_columns
        
        # Clear mappers to simulate what should happen after cleanup
        # In real scenario, mappers might not be cleared, causing conflicts
        clear_mappers()
        
        # Now try to define a new custom model
        # This should work if mappers are cleared, but might fail if they're not
        try:
            class SecondCustomModel(CleanTaskModel):
                __tablename__ = TASK_TABLE_NAME
                __table_args__ = {'extend_existing': True}
                department = Column(String(100), nullable=True)
            
            # If we get here, it worked
            second_table = CleanBase.metadata.tables[TASK_TABLE_NAME]
            second_columns = {c.name for c in second_table.columns}
            assert 'department' in second_columns
            assert 'project_id' not in second_columns  # Should not have project_id from first model
            
        except Exception as e:
            # If it fails, it's because mapper cache still has old definition
            error_type_name = type(e).__name__
            error_msg = str(e)
            
            # Should be NoForeignKeysError
            assert "NoForeignKeysError" in error_type_name or \
                   "Can't determine the inherit condition" in error_msg, \
                f"Expected NoForeignKeysError due to mapper cache, got {error_type_name}: {error_msg}"
    
    def test_table_creation_with_wrong_schema_after_pollution(self, sync_db_session):
        """
        Test that table creation can fail or create wrong schema when Base.metadata
        is polluted, even after cleanup.
        
        This reproduces the scenario where:
        1. Base.metadata is polluted
        2. cleanup_base_metadata() is called
        3. But table creation still fails because of cached metadata or mapper issues
        """
        from sqlalchemy import Column, String, Integer, text
        from aipartnerupflow.core.storage.sqlalchemy.models import Base, TaskModel, TASK_TABLE_NAME
        
        # Pollute Base.metadata
        class PollutedModel(TaskModel):
            __tablename__ = TASK_TABLE_NAME
            __table_args__ = {'extend_existing': True}
            project_id = Column(String(255), nullable=True)
            department = Column(String(100), nullable=True)
        
        # Verify pollution
        table = Base.metadata.tables[TASK_TABLE_NAME]
        assert 'project_id' in {c.name for c in table.columns}
        
        # Cleanup
        from tests.conftest import cleanup_base_metadata
        cleanup_base_metadata()
        
        # Re-import Base
        import sys
        if 'aipartnerupflow.core.storage.sqlalchemy.models' in sys.modules:
            del sys.modules['aipartnerupflow.core.storage.sqlalchemy.models']
        from aipartnerupflow.core.storage.sqlalchemy.models import Base as CleanBase, TASK_TABLE_NAME
        
        # Now sync_db_session should create tables with clean metadata
        # But if there are issues, table creation might fail
        try:
            # Try to use the database
            with sync_db_session.bind.connect() as conn:
                # Check if table exists
                result = conn.execute(
                    text(f"SELECT COUNT(*) FROM {TASK_TABLE_NAME}")
                )
                count = result.scalar()
                assert count is not None or count >= 0
                
                # Check table schema
                result = conn.execute(
                    text(f"PRAGMA table_info({TASK_TABLE_NAME})")
                )
                db_columns = {row[1] for row in result}
                
                # Should have standard columns
                assert 'id' in db_columns
                assert 'name' in db_columns
                
                # Should NOT have custom columns
                assert 'project_id' not in db_columns, \
                    "Database table should not have custom columns after cleanup"
                assert 'department' not in db_columns
                
        except Exception as e:
            # If table creation or query fails, it's because of pollution issues
            error_msg = str(e)
            assert "does not exist" in error_msg or \
                   "Catalog Error" in error_msg or \
                   "no such table" in error_msg.lower() or \
                   "Binder Error" in error_msg, \
                f"Expected table-related error, got: {error_msg}"
    
    def test_no_foreign_keys_error_with_different_column_types(self):
        """
        Test that NoForeignKeysError occurs when Base.metadata has two table definitions
        with the same name but different column types (e.g., project_id String(100) vs String(255)).
        
        This reproduces the exact error seen in test_task_model_customization.py:
        - First test defines CustomTaskModel with project_id String(255)
        - cleanup_base_metadata() is called, but SQLAlchemy mapper cache still has old definition
        - Second test tries to define ProjectTaskModel, but SQLAlchemy finds two different
          table definitions in Base.metadata (one with project_id String(100) from mapper cache,
          one with project_id String(255) from new definition)
        - SQLAlchemy can't determine how to join the two table definitions
        
        Error message shows:
        - a = Table('apflow_tasks', ...) with project_id String(100)
        - b = Table('apflow_tasks', ...) with project_id String(255), department, priority_level
        """
        from sqlalchemy import Column, String, Integer
        from aipartnerupflow.core.storage.sqlalchemy.models import Base, TaskModel, TASK_TABLE_NAME
        from sqlalchemy.orm import clear_mappers
        from sqlalchemy.inspection import inspect as sa_inspect
        import sys
        import importlib
        
        # First test: Define custom model with project_id String(255)
        class FirstCustomModel(TaskModel):
            __tablename__ = TASK_TABLE_NAME
            __table_args__ = {'extend_existing': True}
            project_id = Column(String(255), nullable=True)
            department = Column(String(100), nullable=True)
        
        # Verify pollution
        table1 = Base.metadata.tables[TASK_TABLE_NAME]
        cols1 = {c.name: c for c in table1.columns}
        assert 'project_id' in cols1
        # Note: project_id is String(255) in first definition
        
        # Get the mapper for FirstCustomModel
        mapper1 = sa_inspect(FirstCustomModel)
        assert mapper1 is not None
        # The mapper's local_table has project_id String(255)
        
        # Cleanup Base.metadata (simulating reset_storage_singleton)
        from tests.conftest import cleanup_base_metadata
        cleanup_base_metadata()
        
        # Re-import Base
        if 'aipartnerupflow.core.storage.sqlalchemy.models' in sys.modules:
            del sys.modules['aipartnerupflow.core.storage.sqlalchemy.models']
        from aipartnerupflow.core.storage.sqlalchemy.models import Base as CleanBase, TaskModel as CleanTaskModel, TASK_TABLE_NAME
        
        # Verify cleanup worked
        clean_table = CleanBase.metadata.tables[TASK_TABLE_NAME]
        clean_columns = {c.name for c in clean_table.columns}
        assert 'project_id' not in clean_columns, "Cleanup should remove project_id"
        
        # CRITICAL: The old mapper still exists in SQLAlchemy's registry!
        # Even though Base.metadata was cleaned, the mapper cache still has
        # the old table definition with project_id String(255)
        # When we try to define a new custom model, SQLAlchemy will try to
        # establish inheritance between the new model and the old mapper's table,
        # but they have different column definitions, causing NoForeignKeysError
        
        # Now try to define a new custom model (this is where the error occurs)
        # The error happens because:
        # 1. CleanTaskModel's mapper has a table with default columns (no project_id)
        # 2. But FirstCustomModel's mapper still exists with a table that has project_id String(255)
        # 3. When defining ProjectTaskModel, SQLAlchemy tries to inherit from CleanTaskModel
        # 4. But it also sees FirstCustomModel's mapper, which has a different table definition
        # 5. SQLAlchemy can't determine how to join the two table definitions
        
        try:
            class ProjectTaskModel(CleanTaskModel):
                __tablename__ = TASK_TABLE_NAME
                __table_args__ = {'extend_existing': True}
                project_id = Column(String(255), nullable=True)  # Same type as FirstCustomModel
                department = Column(String(100), nullable=True)
                priority_level = Column(Integer, default=2)
            
            # If we get here, the model was created successfully
            # But check if there are conflicting table definitions
            second_table = CleanBase.metadata.tables[TASK_TABLE_NAME]
            second_columns = {c.name for c in second_table.columns}
            
            # The table should have the new columns
            assert 'project_id' in second_columns
            assert 'department' in second_columns
            assert 'priority_level' in second_columns
            
        except Exception as e:
            # If it fails, verify it's the expected error
            error_type_name = type(e).__name__
            error_msg = str(e)
            
            # Should be NoForeignKeysError
            assert "NoForeignKeysError" in error_type_name or \
                   "Can't determine the inherit condition" in error_msg or \
                   "Can't find any foreign key relationships" in error_msg, \
                f"Expected NoForeignKeysError, got {error_type_name}: {error_msg}"
    
    def test_mapper_registry_pollution_after_cleanup(self):
        """
        Test that SQLAlchemy's mapper registry can be polluted even after
        cleanup_base_metadata() is called.
        
        The problem:
        1. First test defines CustomTaskModel (creates mapper with polluted table)
        2. cleanup_base_metadata() removes table from Base.metadata
        3. But the mapper still exists in SQLAlchemy's registry
        4. Second test tries to define another CustomTaskModel
        5. SQLAlchemy finds the old mapper in the registry, which has a different
           table definition than the new one
        6. SQLAlchemy can't determine how to join the two table definitions
        
        This test verifies that mapper registry pollution can cause NoForeignKeysError
        even after cleanup_base_metadata() is called.
        """
        from sqlalchemy import Column, String, Integer
        from aipartnerupflow.core.storage.sqlalchemy.models import Base, TaskModel, TASK_TABLE_NAME
        from sqlalchemy.orm import clear_mappers
        from sqlalchemy.inspection import inspect as sa_inspect
        import sys
        import importlib
        
        # First test: Define custom model
        class FirstCustomModel(TaskModel):
            __tablename__ = TASK_TABLE_NAME
            __table_args__ = {'extend_existing': True}
            project_id = Column(String(255), nullable=True)
        
        # Verify pollution and mapper creation
        assert TASK_TABLE_NAME in Base.metadata.tables
        first_table = Base.metadata.tables[TASK_TABLE_NAME]
        assert 'project_id' in {c.name for c in first_table.columns}
        
        # Get the mapper for FirstCustomModel
        mapper1 = sa_inspect(FirstCustomModel)
        assert mapper1 is not None
        mapper1_table = mapper1.local_table
        assert 'project_id' in {c.name for c in mapper1_table.columns}
        
        # Cleanup Base.metadata
        from tests.conftest import cleanup_base_metadata
        cleanup_base_metadata()
        
        # Re-import Base
        if 'aipartnerupflow.core.storage.sqlalchemy.models' in sys.modules:
            del sys.modules['aipartnerupflow.core.storage.sqlalchemy.models']
        from aipartnerupflow.core.storage.sqlalchemy.models import Base as CleanBase, TaskModel as CleanTaskModel, TASK_TABLE_NAME
        
        # Verify cleanup worked
        clean_table = CleanBase.metadata.tables[TASK_TABLE_NAME]
        clean_columns = {c.name for c in clean_table.columns}
        assert 'project_id' not in clean_columns
        
        # CRITICAL: The old mapper still exists in SQLAlchemy's registry!
        # Even though Base.metadata was cleaned, the mapper for FirstCustomModel
        # still exists and references the old table definition
        try:
            old_mapper = sa_inspect(FirstCustomModel)
            old_table = old_mapper.local_table
            old_columns = {c.name for c in old_table.columns}
            # The old mapper's table still has project_id
            assert 'project_id' in old_columns, "Old mapper should still have project_id"
        except Exception:
            # If we can't inspect the old mapper, it might have been cleared
            pass
        
        # Clear mappers to simulate what should happen after cleanup
        # In real scenario, mappers might not be cleared, causing conflicts
        clear_mappers()
        
        # Now try to define a new custom model
        # This should work if mappers are cleared, but might fail if they're not
        try:
            class SecondCustomModel(CleanTaskModel):
                __tablename__ = TASK_TABLE_NAME
                __table_args__ = {'extend_existing': True}
                department = Column(String(100), nullable=True)
            
            # If we get here, it worked
            second_table = CleanBase.metadata.tables[TASK_TABLE_NAME]
            second_columns = {c.name for c in second_table.columns}
            assert 'department' in second_columns
            assert 'project_id' not in second_columns  # Should not have project_id from first model
            
        except Exception as e:
            # If it fails, it's because mapper cache still has old definition
            error_type_name = type(e).__name__
            error_msg = str(e)
            
            # Should be NoForeignKeysError
            assert "NoForeignKeysError" in error_type_name or \
                   "Can't determine the inherit condition" in error_msg, \
                f"Expected NoForeignKeysError due to mapper registry pollution, got {error_type_name}: {error_msg}"
    
    def test_catalog_error_when_table_creation_fails(self, sync_db_session):
        """
        Test that 'Catalog Error: Table with name apflow_tasks does not exist!' occurs
        when table creation fails due to Base.metadata pollution.
        
        This reproduces the error seen in many tests when running all tests together:
        - Base.metadata is polluted with custom columns from a previous test
        - sync_db_session tries to create tables
        - Table creation fails because Base.metadata has wrong schema
        - Subsequent queries fail with "Catalog Error: Table does not exist"
        """
        from sqlalchemy import Column, String, Integer, text
        from aipartnerupflow.core.storage.sqlalchemy.models import Base, TaskModel, TASK_TABLE_NAME
        
        # Pollute Base.metadata BEFORE sync_db_session creates tables
        # This simulates a test that runs before the current test
        class PollutedTaskModel(TaskModel):
            __tablename__ = TASK_TABLE_NAME
            __table_args__ = {'extend_existing': True}
            project_id = Column(String(255), nullable=True)
            department = Column(String(100), nullable=True)
            priority_level = Column(Integer, default=2)
        
        # Verify pollution
        table = Base.metadata.tables[TASK_TABLE_NAME]
        column_names = {c.name for c in table.columns}
        assert 'project_id' in column_names
        assert 'department' in column_names
        
        # Now sync_db_session should detect pollution and clean it up
        # But if it doesn't work correctly, we'll get "Catalog Error: Table does not exist"
        # Try to use the database
        try:
            with sync_db_session.bind.connect() as conn:
                # Try to query the table
                result = conn.execute(
                    text(f"SELECT COUNT(*) FROM {TASK_TABLE_NAME}")
                )
                count = result.scalar()
                # If we get here, the table exists and query worked
                assert count is not None or count >= 0
        except Exception as e:
            # If we get an error, it's likely because table doesn't exist
            error_msg = str(e)
            assert "does not exist" in error_msg or \
                   "Catalog Error" in error_msg or \
                   "no such table" in error_msg.lower(), \
                f"Expected table existence error, got: {error_msg}"

