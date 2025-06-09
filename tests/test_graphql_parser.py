"""Tests for GraphQL query parser."""

import pytest

from toady.graphql_parser import (
    GraphQLParser,
    GraphQLOperation,
    GraphQLField,
)


class TestGraphQLParser:
    """Test cases for GraphQLParser."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return GraphQLParser()

    def test_parse_simple_query(self, parser):
        """Test parsing a simple query."""
        query = """
        query {
            user {
                id
                name
            }
        }
        """
        operation = parser.parse(query)

        assert operation.type == "query"
        assert operation.name is None
        assert len(operation.selections) == 1
        assert operation.selections[0].name == "user"
        assert len(operation.selections[0].selections) == 2

    def test_parse_named_query(self, parser):
        """Test parsing a named query."""
        query = """
        query GetUser {
            user {
                id
                name
            }
        }
        """
        operation = parser.parse(query)

        assert operation.type == "query"
        assert operation.name == "GetUser"
        assert len(operation.selections) == 1

    def test_parse_query_with_variables(self, parser):
        """Test parsing query with variables."""
        query = """
        query GetUser($id: ID!, $includeEmail: Boolean) {
            user(id: $id) {
                id
                name
            }
        }
        """
        operation = parser.parse(query)

        assert operation.type == "query"
        assert operation.name == "GetUser"
        assert "id" in operation.variables
        assert operation.variables["id"] == "ID!"
        assert "includeEmail" in operation.variables
        assert operation.variables["includeEmail"] == "Boolean"

    def test_parse_query_with_arguments(self, parser):
        """Test parsing query with field arguments."""
        query = """
        query {
            repository(owner: "octocat", name: "hello-world") {
                id
                name
            }
        }
        """
        operation = parser.parse(query)

        repo_field = operation.selections[0]
        assert repo_field.name == "repository"
        assert repo_field.arguments["owner"] == "octocat"
        assert repo_field.arguments["name"] == "hello-world"

    def test_parse_query_with_variable_arguments(self, parser):
        """Test parsing query with variable arguments."""
        query = """
        query($owner: String!, $name: String!) {
            repository(owner: $owner, name: $name) {
                id
            }
        }
        """
        operation = parser.parse(query)

        repo_field = operation.selections[0]
        assert repo_field.arguments["owner"] == {"variable": "owner"}
        assert repo_field.arguments["name"] == {"variable": "name"}

    def test_parse_query_with_aliases(self, parser):
        """Test parsing query with field aliases."""
        query = """
        query {
            firstUser: user(id: "1") {
                id
                name
            }
            secondUser: user(id: "2") {
                id
                name
            }
        }
        """
        operation = parser.parse(query)

        assert len(operation.selections) == 2
        assert operation.selections[0].alias == "firstUser"
        assert operation.selections[0].name == "user"
        assert operation.selections[1].alias == "secondUser"
        assert operation.selections[1].name == "user"

    def test_parse_mutation(self, parser):
        """Test parsing a mutation."""
        query = """
        mutation ResolveThread($threadId: ID!) {
            resolveReviewThread(input: {threadId: $threadId}) {
                thread {
                    id
                    isResolved
                }
            }
        }
        """
        operation = parser.parse(query)

        assert operation.type == "mutation"
        assert operation.name == "ResolveThread"
        assert "threadId" in operation.variables
        assert len(operation.selections) == 1

    def test_parse_nested_selections(self, parser):
        """Test parsing deeply nested selections."""
        query = """
        query {
            repository(owner: "test", name: "repo") {
                pullRequest(number: 1) {
                    reviewThreads(first: 10) {
                        nodes {
                            id
                            comments {
                                nodes {
                                    body
                                    author {
                                        login
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        operation = parser.parse(query)

        # Navigate through the nested structure
        repo = operation.selections[0]
        assert repo.name == "repository"

        pr = repo.selections[0]
        assert pr.name == "pullRequest"
        assert pr.arguments["number"] == 1

        threads = pr.selections[0]
        assert threads.name == "reviewThreads"
        assert threads.arguments["first"] == 10

        nodes = threads.selections[0]
        assert nodes.name == "nodes"

    def test_parse_fragment_spread_like_pattern(self, parser):
        """Test parsing patterns that look like fragments (but simplified)."""
        query = """
        query {
            user {
                id
                name
                ... on User {
                    email
                }
            }
        }
        """
        # Our parser now handles fragments by treating them as pseudo-fields
        operation = parser.parse(query)
        assert operation.type == "query"
        
        user_field = operation.selections[0]
        assert user_field.name == "user"
        
        # Should have id, name, and the fragment pseudo-field
        field_names = [field.name for field in user_field.selections]
        assert "id" in field_names
        assert "name" in field_names
        assert "__fragment_User" in field_names

    def test_clean_query_removes_comments(self, parser):
        """Test that comments are removed from queries."""
        query = """
        query {
            # This is a comment
            user {
                id # Another comment
                name
            }
        }
        """
        operation = parser.parse(query)

        assert len(operation.selections) == 1
        assert operation.selections[0].name == "user"

    def test_parse_empty_query(self, parser):
        """Test parsing empty query."""
        with pytest.raises(ValueError, match="Invalid GraphQL operation"):
            parser.parse("")

    def test_parse_invalid_query(self, parser):
        """Test parsing invalid query."""
        with pytest.raises(ValueError, match="Invalid GraphQL operation"):
            parser.parse("invalid query")

    def test_parse_query_missing_closing_brace(self, parser):
        """Test parsing query with missing closing brace."""
        query = """
        query {
            user {
                id
        """
        with pytest.raises(ValueError, match="Unmatched braces"):
            parser.parse(query)

    def test_extract_all_fields(self, parser):
        """Test extracting all field names."""
        query = """
        query {
            repository {
                name
                pullRequest {
                    id
                    title
                    reviewThreads {
                        nodes {
                            id
                            isResolved
                        }
                    }
                }
            }
        }
        """
        operation = parser.parse(query)
        fields = parser.extract_all_fields(operation)

        expected_fields = {
            "repository", "name", "pullRequest", "id", "title",
            "reviewThreads", "nodes", "isResolved"
        }
        assert fields == expected_fields

    def test_extract_field_paths(self, parser):
        """Test extracting field paths."""
        query = """
        query {
            repository {
                name
                pullRequest {
                    id
                    title
                }
            }
        }
        """
        operation = parser.parse(query)
        paths = parser.extract_field_paths(operation)

        expected_paths = [
            "repository",
            "repository.name",
            "repository.pullRequest",
            "repository.pullRequest.id",
            "repository.pullRequest.title",
        ]
        assert paths == expected_paths

    def test_parse_query_with_numeric_arguments(self, parser):
        """Test parsing query with numeric arguments."""
        query = """
        query {
            pullRequest(number: 123) {
                id
            }
        }
        """
        operation = parser.parse(query)

        pr_field = operation.selections[0]
        assert pr_field.arguments["number"] == 123

    def test_parse_query_with_boolean_arguments(self, parser):
        """Test parsing query with boolean arguments."""
        query = """
        query {
            issues(first: 10, orderBy: {field: CREATED_AT, direction: DESC}) {
                nodes {
                    id
                }
            }
        }
        """
        operation = parser.parse(query)

        issues_field = operation.selections[0]
        assert issues_field.arguments["first"] == 10
        # Complex arguments are simplified in our parser
        assert "orderBy" in issues_field.arguments

    def test_parse_mutation_with_input_object(self, parser):
        """Test parsing mutation with input object."""
        query = """
        mutation($threadId: ID!) {
            resolveReviewThread(input: {threadId: $threadId}) {
                thread {
                    id
                }
            }
        }
        """
        operation = parser.parse(query)

        resolve_field = operation.selections[0]
        assert resolve_field.name == "resolveReviewThread"
        # Input objects are simplified in our parser
        assert "input" in resolve_field.arguments

    def test_parse_complex_real_world_query(self, parser):
        """Test parsing a complex real-world query."""
        query = """
        query($owner: String!, $repo: String!, $number: Int!) {
            repository(owner: $owner, name: $repo) {
                pullRequest(number: $number) {
                    id
                    number
                    title
                    url
                    reviewThreads(first: 100) {
                        pageInfo {
                            hasNextPage
                            endCursor
                        }
                        nodes {
                            id
                            isResolved
                            isOutdated
                            line
                            originalLine
                            path
                            diffSide
                            startLine
                            originalStartLine
                            comments(first: 10) {
                                pageInfo {
                                    hasNextPage
                                    endCursor
                                }
                                nodes {
                                    id
                                    body
                                    createdAt
                                    updatedAt
                                    author {
                                        login
                                    }
                                    url
                                    replyTo {
                                        id
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        operation = parser.parse(query)

        assert operation.type == "query"
        assert len(operation.variables) == 3
        assert "owner" in operation.variables
        assert "repo" in operation.variables
        assert "number" in operation.variables

        # Verify structure is parsed
        assert len(operation.selections) == 1
        assert operation.selections[0].name == "repository"