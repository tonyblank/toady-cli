"""Simple GraphQL query parser for validation purposes.

This module provides basic GraphQL query parsing functionality
to extract fields, arguments, and structure for validation.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Optional


@dataclass
class GraphQLField:
    """Represents a field in a GraphQL query."""

    name: str
    alias: Optional[str] = None
    arguments: dict[str, Any] = field(default_factory=dict)
    selections: list["GraphQLField"] = field(default_factory=list)
    parent_type: Optional[str] = None


@dataclass
class GraphQLOperation:
    """Represents a GraphQL operation (query/mutation)."""

    type: str  # "query" or "mutation"
    name: Optional[str] = None
    variables: dict[str, str] = field(default_factory=dict)
    selections: list[GraphQLField] = field(default_factory=list)


class GraphQLParser:
    """Simple GraphQL query parser for validation."""

    def __init__(self) -> None:
        """Initialize the parser."""
        self._type_stack: list[str] = []

    def parse(self, query: str) -> GraphQLOperation:
        """Parse a GraphQL query string.

        Args:
            query: GraphQL query string

        Returns:
            Parsed GraphQL operation

        Raises:
            ValueError: If query is invalid
        """
        # Clean up the query
        query = self._clean_query(query)

        # Extract operation
        operation = self._parse_operation(query)

        return operation

    def _clean_query(self, query: str) -> str:
        """Clean up GraphQL query by removing comments and extra whitespace."""
        # Remove single-line comments
        query = re.sub(r"#.*$", "", query, flags=re.MULTILINE)

        # Remove extra whitespace while preserving structure
        query = re.sub(r"\s+", " ", query)
        query = query.strip()

        return query

    def _parse_operation(self, query: str) -> GraphQLOperation:
        """Parse the main operation from the query."""
        # Match operation type and name - support subscriptions and shorthand queries
        op_match = re.match(
            r"^(query|mutation|subscription)?\s*(\w+)?\s*(\([^)]*\))?\s*{",
            query,
            re.IGNORECASE,
        )

        if not op_match:
            raise ValueError("Invalid GraphQL operation format")

        op_type = (
            op_match.group(1) or "query"
        ).lower()  # Default to query for shorthand
        op_name = op_match.group(2)
        variables_str = op_match.group(3)

        # Parse variables if present
        variables = {}
        if variables_str:
            variables = self._parse_variables(variables_str)

        # Find the main selection set
        selection_start = query.find("{", op_match.end() - 1)
        selection_end = self._find_matching_brace(query, selection_start)

        if selection_end == -1:
            raise ValueError("Unmatched braces in query")

        selection_str = query[selection_start + 1 : selection_end]

        # Parse selections
        selections = self._parse_selections(selection_str, op_type.capitalize())

        return GraphQLOperation(
            type=op_type,
            name=op_name,
            variables=variables,
            selections=selections,
        )

    def _parse_variables(self, variables_str: str) -> dict[str, str]:
        """Parse variable declarations."""
        variables = {}

        # Remove parentheses
        variables_str = variables_str.strip("()")

        # Simple variable parsing (doesn't handle all cases)
        var_pattern = r"\$(\w+)\s*:\s*([^,\s]+)"
        for match in re.finditer(var_pattern, variables_str):
            var_name = match.group(1)
            var_type = match.group(2)
            variables[var_name] = var_type

        return variables

    def _parse_selections(
        self, selection_str: str, parent_type: str
    ) -> list[GraphQLField]:
        """Parse a selection set."""
        selections = []
        current_pos = 0

        while current_pos < len(selection_str):
            # Skip whitespace
            while (
                current_pos < len(selection_str)
                and selection_str[current_pos].isspace()
            ):
                current_pos += 1

            if current_pos >= len(selection_str):
                break

            # Parse field
            field, next_pos = self._parse_field(selection_str, current_pos, parent_type)
            if field:
                selections.append(field)

            current_pos = next_pos

        return selections

    def _parse_field(
        self, selection_str: str, start_pos: int, parent_type: str
    ) -> tuple[Optional[GraphQLField], int]:
        """Parse a single field from the selection set."""
        # Skip whitespace
        while start_pos < len(selection_str) and selection_str[start_pos].isspace():
            start_pos += 1

        if start_pos >= len(selection_str):
            return None, start_pos

        # Check for inline fragment (... on Type)
        if selection_str[start_pos : start_pos + 3] == "...":
            return self._parse_inline_fragment(selection_str, start_pos, parent_type)

        # Match field pattern: [alias:] fieldName [(args)] [{selections}]
        field_pattern = r"(\w+\s*:\s*)?(\w+)\s*(\([^)]*\))?\s*({)?"

        match = re.match(field_pattern, selection_str[start_pos:])
        if not match:
            return None, start_pos + 1

        alias_part = match.group(1)
        field_name = match.group(2)
        args_part = match.group(3)
        has_selections = match.group(4) is not None

        # Extract alias if present
        alias = None
        if alias_part:
            alias = alias_part.strip().rstrip(":")

        # Parse arguments
        arguments = {}
        if args_part:
            arguments = self._parse_arguments(args_part)

        # Parse nested selections if present
        selections = []
        next_pos = start_pos + match.end()

        if has_selections:
            # Find matching brace
            selection_start = start_pos + match.end() - 1
            selection_end = self._find_matching_brace(selection_str, selection_start)

            if selection_end == -1:
                raise ValueError(f"Unmatched braces for field {field_name}")

            nested_str = selection_str[selection_start + 1 : selection_end]
            selections = self._parse_selections(nested_str, field_name)
            next_pos = selection_end + 1

        field = GraphQLField(
            name=field_name,
            alias=alias,
            arguments=arguments,
            selections=selections,
            parent_type=parent_type,
        )

        return field, next_pos

    def _parse_inline_fragment(
        self, selection_str: str, start_pos: int, parent_type: str
    ) -> tuple[Optional[GraphQLField], int]:
        """Parse an inline fragment (... on Type)."""
        # Pattern for inline fragment: ... on TypeName { selections }
        fragment_pattern = r"\.\.\.\s+on\s+(\w+)\s*{"

        match = re.match(fragment_pattern, selection_str[start_pos:])
        if not match:
            # Skip this fragment for now
            next_brace = selection_str.find("{", start_pos)
            if next_brace == -1:
                return None, len(selection_str)

            end_brace = self._find_matching_brace(selection_str, next_brace)
            if end_brace == -1:
                return None, len(selection_str)

            return None, end_brace + 1

        type_name = match.group(1)

        # Find the opening brace
        selection_start = start_pos + match.end() - 1
        selection_end = self._find_matching_brace(selection_str, selection_start)

        if selection_end == -1:
            raise ValueError(f"Unmatched braces for inline fragment on {type_name}")

        # Parse the fragment's selections
        nested_str = selection_str[selection_start + 1 : selection_end]
        selections = self._parse_selections(nested_str, type_name)

        # Create a pseudo-field for the inline fragment
        # We'll treat it as a field with a special name
        field = GraphQLField(
            name=f"__fragment_{type_name}",
            alias=None,
            arguments={},
            selections=selections,
            parent_type=parent_type,
        )

        return field, selection_end + 1

    def _parse_arguments(self, args_str: str) -> dict[str, Any]:
        """Parse field arguments."""
        arguments = {}

        # Remove parentheses
        args_str = args_str.strip("()")

        # Simple argument parsing
        arg_pattern = r"(\w+)\s*:\s*([^,]+)"
        for match in re.finditer(arg_pattern, args_str):
            arg_name = match.group(1)
            arg_value = match.group(2).strip()

            # Handle different value types
            parsed_value: Any
            if arg_value.startswith("$"):
                # Variable reference
                parsed_value = {"variable": arg_value[1:]}
            elif arg_value.startswith('"') or arg_value.startswith("'"):
                # String literal
                parsed_value = arg_value.strip("\"'")
            elif arg_value.isdigit():
                # Number
                parsed_value = int(arg_value)
            else:
                # Other (boolean, enum, etc.)
                parsed_value = arg_value

            arguments[arg_name] = parsed_value

        return arguments

    def _find_matching_brace(self, text: str, start_pos: int, offset: int = 0) -> int:
        """Find the matching closing brace for an opening brace."""
        if start_pos >= len(text) or text[start_pos] != "{":
            return -1

        count = 0
        in_string = False
        escape_next = False

        for i in range(start_pos, len(text)):
            char = text[i]

            if escape_next:
                escape_next = False
                continue

            if char == "\\":
                escape_next = True
                continue

            if char == '"' and not in_string:
                in_string = True
            elif char == '"' and in_string:
                in_string = False
            elif not in_string:
                if char == "{":
                    count += 1
                elif char == "}":
                    count -= 1
                    if count == 0:
                        return i + offset

        return -1

    def extract_all_fields(self, operation: GraphQLOperation) -> set[str]:
        """Extract all field names from an operation.

        Args:
            operation: Parsed GraphQL operation

        Returns:
            Set of all field names used in the query
        """
        fields = set()

        def collect_fields(selections: list[GraphQLField]) -> None:
            for selection in selections:
                fields.add(selection.name)
                if selection.selections:
                    collect_fields(selection.selections)

        collect_fields(operation.selections)
        return fields

    def extract_field_paths(self, operation: GraphQLOperation) -> list[str]:
        """Extract all field paths from an operation.

        Args:
            operation: Parsed GraphQL operation

        Returns:
            List of field paths (e.g., ["repository.pullRequest.id"])
        """
        paths = []

        def collect_paths(
            selections: list[GraphQLField], parent_path: str = ""
        ) -> None:
            for selection in selections:
                current_path = (
                    f"{parent_path}.{selection.name}" if parent_path else selection.name
                )
                paths.append(current_path)

                if selection.selections:
                    collect_paths(selection.selections, current_path)

        collect_paths(operation.selections)
        return paths
