"""Tests for persistence layer (LearningStore and PatternExtractor)"""

import pytest
import tempfile
import os
from pathlib import Path

from jester.persistence.store import LearningStore
from jester.persistence.patterns import PatternExtractor, ExtractedPattern
from jester.core.models import ValidationResult, ExecutionResult, ExecutionTier


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def learning_store(temp_db):
    """Create a LearningStore with temporary database"""
    return LearningStore(db_path=temp_db)


@pytest.fixture
def pattern_extractor():
    """Create a PatternExtractor instance"""
    return PatternExtractor()


class TestLearningStore:
    """Tests for LearningStore"""

    def test_initialization(self, learning_store):
        """Test that store initializes correctly"""
        stats = learning_store.get_global_stats()
        assert stats["total_executions"] == 0
        assert stats["success_rate"] == 0

    def test_record_successful_execution(self, learning_store):
        """Test recording a successful execution"""
        code = """
def add(a, b):
    return a + b

result = add(1, 2)
print(result)
"""
        result = ValidationResult(
            code_id="test1",
            syntax_valid=True,
            executes=True,
            complexity_score=2,
            patterns_detected=["function_definition"],
            execution_result=ExecutionResult(
                success=True,
                output="3\n",
                execution_time_ms=10.0,
                tier=ExecutionTier.REPL,
                memory_usage_mb=1.0
            )
        )

        exec_id = learning_store.record_execution(code, result)
        assert exec_id > 0

        stats = learning_store.get_global_stats()
        assert stats["total_executions"] == 1
        assert stats["success_rate"] == 1.0

    def test_record_failed_execution(self, learning_store):
        """Test recording a failed execution"""
        code = "1 / 0"
        result = ValidationResult(
            code_id="test2",
            syntax_valid=True,
            executes=False,
            issues=["Division by zero"],
            execution_result=ExecutionResult(
                success=False,
                error="ZeroDivisionError: division by zero",
                execution_time_ms=5.0,
                tier=ExecutionTier.REPL
            )
        )

        exec_id = learning_store.record_execution(code, result)
        assert exec_id > 0

        stats = learning_store.get_global_stats()
        assert stats["total_executions"] == 1
        assert stats["success_rate"] == 0.0

    def test_get_similar_executions(self, learning_store):
        """Test finding similar executions by code hash"""
        code = "x = 42"
        result = ValidationResult(
            code_id="test3",
            syntax_valid=True,
            executes=True,
            execution_result=ExecutionResult(success=True, tier=ExecutionTier.REPL)
        )

        # Record same code multiple times
        learning_store.record_execution(code, result)
        learning_store.record_execution(code, result)

        similar = learning_store.get_similar_executions(code)
        assert len(similar) == 2

    def test_function_stats(self, learning_store):
        """Test getting function statistics"""
        code = """
def my_function(x):
    return x * 2
"""
        result = ValidationResult(
            code_id="test4",
            syntax_valid=True,
            executes=True,
            complexity_score=1,
            execution_result=ExecutionResult(
                success=True,
                execution_time_ms=5.0,
                tier=ExecutionTier.REPL
            )
        )

        learning_store.record_execution(code, result)

        stats = learning_store.get_function_stats("my_function")
        assert stats is not None
        assert stats["name"] == "my_function"
        assert stats["success_count"] == 1

    def test_pattern_tracking(self, learning_store):
        """Test that patterns are tracked"""
        code = "x = [i**2 for i in range(10)]"
        result = ValidationResult(
            code_id="test5",
            syntax_valid=True,
            executes=True,
            patterns_detected=["list_comprehension"],
            execution_result=ExecutionResult(
                success=True,
                execution_time_ms=5.0,
                tier=ExecutionTier.REPL
            )
        )

        learning_store.record_execution(code, result)

        stats = learning_store.get_pattern_stats("list_comprehension")
        assert stats is not None
        assert stats["success_count"] == 1

    def test_error_pattern_recording(self, learning_store):
        """Test that error patterns are recorded"""
        code = "undefined_variable"
        result = ValidationResult(
            code_id="test6",
            syntax_valid=True,
            executes=False,
            execution_result=ExecutionResult(
                success=False,
                error="NameError: name 'undefined_variable' is not defined",
                tier=ExecutionTier.REPL
            )
        )

        learning_store.record_execution(code, result)

        errors = learning_store.get_common_errors("NameError")
        assert len(errors) > 0

    def test_export_training_data(self, learning_store, tmp_path):
        """Test exporting training data"""
        code = """
def hello_world():
    print("Hello, World!")

hello_world()
"""
        result = ValidationResult(
            code_id="test7",
            syntax_valid=True,
            executes=True,
            execution_result=ExecutionResult(
                success=True,
                output="Hello, World!\n",
                tier=ExecutionTier.REPL
            )
        )

        learning_store.record_execution(code, result)

        output_file = tmp_path / "training.jsonl"
        count = learning_store.export_training_data(str(output_file))

        assert count == 1
        assert output_file.exists()

        import json
        with open(output_file) as f:
            data = json.loads(f.readline())
            assert "instruction" in data
            assert "output" in data

    def test_cleanup_old_records(self, learning_store):
        """Test cleanup of old records"""
        # Record an execution
        code = "x = 1"
        result = ValidationResult(
            code_id="test8",
            syntax_valid=True,
            executes=True,
            execution_result=ExecutionResult(success=True, tier=ExecutionTier.REPL)
        )

        learning_store.record_execution(code, result)

        # Cleanup with 0 days should remove everything
        removed = learning_store.cleanup_old_records(days=0)
        assert removed == 1


class TestPatternExtractor:
    """Tests for PatternExtractor"""

    def test_extract_function_definition(self, pattern_extractor):
        """Test extracting function definitions"""
        code = """
def my_func(x, y):
    return x + y
"""
        patterns = pattern_extractor.extract_patterns(code)
        pattern_names = [p.name for p in patterns]
        assert "function_definition" in pattern_names

    def test_extract_class_definition(self, pattern_extractor):
        """Test extracting class definitions"""
        code = """
class MyClass:
    def __init__(self):
        pass
"""
        patterns = pattern_extractor.extract_patterns(code)
        pattern_names = [p.name for p in patterns]
        assert "class_definition" in pattern_names

    def test_extract_async_function(self, pattern_extractor):
        """Test extracting async functions"""
        code = """
async def async_func():
    await some_async_call()
"""
        patterns = pattern_extractor.extract_patterns(code)
        pattern_names = [p.name for p in patterns]
        assert "async_function" in pattern_names

    def test_extract_decorators(self, pattern_extractor):
        """Test extracting decorator usage"""
        code = """
@property
def my_property(self):
    return self._value

@staticmethod
def my_static():
    pass
"""
        patterns = pattern_extractor.extract_patterns(code)
        pattern_names = [p.name for p in patterns]
        assert "property_usage" in pattern_names
        assert "static_method" in pattern_names

    def test_extract_list_comprehension(self, pattern_extractor):
        """Test extracting list comprehension idiom"""
        code = "squares = [x**2 for x in range(10)]"
        patterns = pattern_extractor.extract_patterns(code)
        pattern_names = [p.name for p in patterns]
        assert "list_comprehension" in pattern_names

    def test_extract_context_manager(self, pattern_extractor):
        """Test extracting context manager usage"""
        code = """
with open('file.txt') as f:
    data = f.read()
"""
        patterns = pattern_extractor.extract_patterns(code)
        pattern_names = [p.name for p in patterns]
        assert "context_manager" in pattern_names

    def test_extract_f_string(self, pattern_extractor):
        """Test extracting f-string usage"""
        code = 'message = f"Hello, {name}!"'
        patterns = pattern_extractor.extract_patterns(code)
        pattern_names = [p.name for p in patterns]
        assert "f_string" in pattern_names

    def test_extract_type_hints(self, pattern_extractor):
        """Test extracting type hints"""
        code = """
def greet(name: str) -> str:
    return f"Hello, {name}"
"""
        patterns = pattern_extractor.extract_patterns(code)
        pattern_names = [p.name for p in patterns]
        assert "type_hints" in pattern_names

    def test_detect_singleton_pattern(self, pattern_extractor):
        """Test detecting singleton design pattern"""
        code = """
class Singleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
"""
        patterns = pattern_extractor.extract_patterns(code)
        pattern_names = [p.name for p in patterns]
        assert "singleton" in pattern_names

    def test_detect_factory_pattern(self, pattern_extractor):
        """Test detecting factory design pattern"""
        code = """
class AnimalFactory:
    def create_animal(self, animal_type):
        if animal_type == "dog":
            return Dog()
        elif animal_type == "cat":
            return Cat()
"""
        patterns = pattern_extractor.extract_patterns(code)
        pattern_names = [p.name for p in patterns]
        assert "factory" in pattern_names

    def test_pattern_summary(self, pattern_extractor):
        """Test pattern summary generation"""
        code = """
class MyClass:
    @property
    def value(self):
        return [x for x in self._data]
"""
        patterns = pattern_extractor.extract_patterns(code)
        summary = pattern_extractor.get_pattern_summary(patterns)

        assert "total" in summary
        assert "by_type" in summary
        assert "by_name" in summary
        assert summary["total"] > 0

    def test_compare_patterns(self, pattern_extractor):
        """Test pattern comparison between code versions"""
        code1 = "x = 1"
        code2 = """
def func():
    return [i for i in range(10)]
"""
        patterns1 = pattern_extractor.extract_patterns(code1)
        patterns2 = pattern_extractor.extract_patterns(code2)

        comparison = pattern_extractor.compare_patterns(patterns1, patterns2)

        assert "added" in comparison
        assert "removed" in comparison
        assert "common" in comparison
        assert len(comparison["added"]) > 0  # New patterns in code2

    def test_invalid_syntax_handling(self, pattern_extractor):
        """Test that invalid syntax is handled gracefully"""
        code = "def broken("
        patterns = pattern_extractor.extract_patterns(code)
        # Should not raise, may return empty or partial results
        assert isinstance(patterns, list)

    def test_dataclass_detection(self, pattern_extractor):
        """Test detecting dataclass pattern"""
        code = """
from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float
"""
        patterns = pattern_extractor.extract_patterns(code)
        pattern_names = [p.name for p in patterns]
        assert "dataclass" in pattern_names
