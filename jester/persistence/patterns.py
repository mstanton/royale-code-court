"""
Pattern extraction utilities for Code Jester.
Extracts structural and semantic patterns from code.
"""

import ast
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class ExtractedPattern:
    """A pattern extracted from code"""
    pattern_type: str  # structural, semantic, idiom
    name: str
    description: str
    locations: List[int] = field(default_factory=list)  # Line numbers
    confidence: float = 1.0


class PatternExtractor:
    """
    Extracts patterns from Python code for learning.

    Detects:
    - Structural patterns (classes, functions, decorators)
    - Semantic patterns (idioms, design patterns)
    - Error-prone patterns (antipatterns)
    """

    # Structural patterns
    STRUCTURAL_PATTERNS = {
        "class_definition": "Class defined",
        "function_definition": "Function defined",
        "async_function": "Async function",
        "decorator_usage": "Decorator pattern",
        "property_usage": "Property decorator",
        "static_method": "Static method",
        "class_method": "Class method",
        "dataclass": "Dataclass pattern",
        "abstract_class": "Abstract base class",
    }

    # Idiom patterns (via regex on code)
    IDIOM_PATTERNS = {
        "list_comprehension": (r'\[.*for.*in.*\]', "List comprehension"),
        "dict_comprehension": (r'\{.*:.*for.*in.*\}', "Dict comprehension"),
        "generator_expression": (r'\(.*for.*in.*\)', "Generator expression"),
        "context_manager": (r'with\s+.*:', "Context manager usage"),
        "ternary_expression": (r'if.*else.*', "Ternary/conditional expression"),
        "f_string": (r'f["\']', "F-string formatting"),
        "walrus_operator": (r':=', "Walrus operator"),
        "type_hints": (r'def\s+\w+\([^)]*:\s*\w+', "Type hints"),
        "unpacking": (r'\*\*?\w+', "Argument unpacking"),
        "exception_chaining": (r'raise.*from', "Exception chaining"),
    }

    # Design patterns (heuristic detection)
    DESIGN_PATTERNS = {
        "singleton": ["__new__", "_instance"],
        "factory": ["create_", "factory", "Factory"],
        "builder": ["build", "Builder", "with_"],
        "observer": ["subscribe", "notify", "Observer"],
        "strategy": ["Strategy", "execute", "algorithm"],
        "decorator_pattern": ["wrapper", "decorated", "Decorator"],
    }

    def __init__(self):
        pass

    def extract_patterns(self, code: str) -> List[ExtractedPattern]:
        """
        Extract all patterns from code.

        Args:
            code: Python source code

        Returns:
            List of extracted patterns
        """
        patterns = []

        # Extract structural patterns from AST
        patterns.extend(self._extract_structural_patterns(code))

        # Extract idiom patterns via regex
        patterns.extend(self._extract_idiom_patterns(code))

        # Try to detect design patterns
        patterns.extend(self._detect_design_patterns(code))

        return patterns

    def _extract_structural_patterns(self, code: str) -> List[ExtractedPattern]:
        """Extract patterns from AST analysis"""
        patterns = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return patterns

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                patterns.append(ExtractedPattern(
                    pattern_type="structural",
                    name="class_definition",
                    description=f"Class '{node.name}' defined",
                    locations=[node.lineno]
                ))

                # Check for dataclass
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
                        patterns.append(ExtractedPattern(
                            pattern_type="structural",
                            name="dataclass",
                            description=f"Dataclass '{node.name}'",
                            locations=[node.lineno]
                        ))
                    elif isinstance(decorator, ast.Attribute) and decorator.attr == "dataclass":
                        patterns.append(ExtractedPattern(
                            pattern_type="structural",
                            name="dataclass",
                            description=f"Dataclass '{node.name}'",
                            locations=[node.lineno]
                        ))

                # Check for ABC
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id in ("ABC", "ABCMeta"):
                        patterns.append(ExtractedPattern(
                            pattern_type="structural",
                            name="abstract_class",
                            description=f"Abstract class '{node.name}'",
                            locations=[node.lineno]
                        ))

            elif isinstance(node, ast.FunctionDef):
                patterns.append(ExtractedPattern(
                    pattern_type="structural",
                    name="function_definition",
                    description=f"Function '{node.name}' defined",
                    locations=[node.lineno]
                ))

                # Check decorators
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name):
                        if decorator.id == "property":
                            patterns.append(ExtractedPattern(
                                pattern_type="structural",
                                name="property_usage",
                                description=f"Property '{node.name}'",
                                locations=[node.lineno]
                            ))
                        elif decorator.id == "staticmethod":
                            patterns.append(ExtractedPattern(
                                pattern_type="structural",
                                name="static_method",
                                description=f"Static method '{node.name}'",
                                locations=[node.lineno]
                            ))
                        elif decorator.id == "classmethod":
                            patterns.append(ExtractedPattern(
                                pattern_type="structural",
                                name="class_method",
                                description=f"Class method '{node.name}'",
                                locations=[node.lineno]
                            ))
                        else:
                            patterns.append(ExtractedPattern(
                                pattern_type="structural",
                                name="decorator_usage",
                                description=f"Decorator @{decorator.id}",
                                locations=[node.lineno]
                            ))

            elif isinstance(node, ast.AsyncFunctionDef):
                patterns.append(ExtractedPattern(
                    pattern_type="structural",
                    name="async_function",
                    description=f"Async function '{node.name}'",
                    locations=[node.lineno]
                ))

        return patterns

    def _extract_idiom_patterns(self, code: str) -> List[ExtractedPattern]:
        """Extract idiom patterns via regex matching"""
        patterns = []
        lines = code.split('\n')

        for pattern_name, (regex, description) in self.IDIOM_PATTERNS.items():
            for i, line in enumerate(lines, 1):
                if re.search(regex, line):
                    patterns.append(ExtractedPattern(
                        pattern_type="idiom",
                        name=pattern_name,
                        description=description,
                        locations=[i],
                        confidence=0.8
                    ))

        return patterns

    def _detect_design_patterns(self, code: str) -> List[ExtractedPattern]:
        """Heuristically detect design patterns"""
        patterns = []

        for pattern_name, indicators in self.DESIGN_PATTERNS.items():
            matches = sum(1 for ind in indicators if ind in code)
            if matches >= 2:  # At least 2 indicators
                confidence = min(1.0, matches * 0.3)
                patterns.append(ExtractedPattern(
                    pattern_type="design",
                    name=pattern_name,
                    description=f"Possible {pattern_name.replace('_', ' ').title()} pattern",
                    confidence=confidence
                ))

        return patterns

    def get_pattern_summary(self, patterns: List[ExtractedPattern]) -> Dict[str, Any]:
        """
        Get a summary of extracted patterns.

        Args:
            patterns: List of extracted patterns

        Returns:
            Summary dict with counts and details
        """
        summary = {
            "total": len(patterns),
            "by_type": {},
            "by_name": {},
            "high_confidence": []
        }

        for pattern in patterns:
            # Count by type
            if pattern.pattern_type not in summary["by_type"]:
                summary["by_type"][pattern.pattern_type] = 0
            summary["by_type"][pattern.pattern_type] += 1

            # Count by name
            if pattern.name not in summary["by_name"]:
                summary["by_name"][pattern.name] = 0
            summary["by_name"][pattern.name] += 1

            # Track high confidence patterns
            if pattern.confidence >= 0.9:
                summary["high_confidence"].append({
                    "name": pattern.name,
                    "description": pattern.description
                })

        return summary

    def compare_patterns(
        self,
        patterns1: List[ExtractedPattern],
        patterns2: List[ExtractedPattern]
    ) -> Dict[str, Any]:
        """
        Compare patterns between two code samples.

        Useful for understanding how code evolved.

        Args:
            patterns1: Patterns from first code sample
            patterns2: Patterns from second code sample

        Returns:
            Comparison results
        """
        names1 = set(p.name for p in patterns1)
        names2 = set(p.name for p in patterns2)

        return {
            "added": list(names2 - names1),
            "removed": list(names1 - names2),
            "common": list(names1 & names2),
            "count_change": len(patterns2) - len(patterns1)
        }
