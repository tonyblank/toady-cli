"""Tests for the parsers module."""

from datetime import datetime

import pytest

from toady.parsers import GraphQLResponseParser, ResponseValidator


class TestGraphQLResponseParser:
    """Test the GraphQLResponseParser class."""

    def test_init(self) -> None:
        """Test parser initialization."""
        parser = GraphQLResponseParser()
        assert parser is not None

    def test_parse_review_threads_response_success(self) -> None:
        """Test successful parsing of review threads response."""
        parser = GraphQLResponseParser()

        response = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "id": "RT_kwDOAbc123",
                                    "isResolved": False,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "id": "IC_kwDOAbc123",
                                                "body": "This is a test comment",
                                                "createdAt": "2024-01-15T10:30:00Z",
                                                "updatedAt": "2024-01-15T10:30:00Z",
                                                "author": {"login": "testuser"},
                                                "replyTo": None,
                                            }
                                        ]
                                    },
                                }
                            ]
                        }
                    }
                }
            }
        }

        threads = parser.parse_review_threads_response(response)

        assert len(threads) == 1
        thread = threads[0]
        assert thread.thread_id == "RT_kwDOAbc123"
        assert thread.title == "This is a test comment"
        assert thread.status == "UNRESOLVED"
        assert thread.author == "testuser"
        assert len(thread.comments) == 1

    def test_parse_review_threads_response_with_multiple_threads(self) -> None:
        """Test parsing response with multiple review threads."""
        parser = GraphQLResponseParser()

        response = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "nodes": [
                                {
                                    "id": "RT_1",
                                    "isResolved": True,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "id": "IC_1",
                                                "body": "First comment",
                                                "createdAt": "2024-01-15T10:30:00Z",
                                                "updatedAt": "2024-01-15T10:30:00Z",
                                                "author": {"login": "user1"},
                                                "replyTo": None,
                                            }
                                        ]
                                    },
                                },
                                {
                                    "id": "RT_2",
                                    "isResolved": False,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "id": "IC_2",
                                                "body": "Second comment",
                                                "createdAt": "2024-01-15T11:00:00Z",
                                                "updatedAt": "2024-01-15T11:00:00Z",
                                                "author": {"login": "user2"},
                                                "replyTo": None,
                                            }
                                        ]
                                    },
                                },
                            ]
                        }
                    }
                }
            }
        }

        threads = parser.parse_review_threads_response(response)

        assert len(threads) == 2
        assert threads[0].thread_id == "RT_1"
        assert threads[0].status == "RESOLVED"
        assert threads[1].thread_id == "RT_2"
        assert threads[1].status == "UNRESOLVED"

    def test_parse_review_threads_response_invalid_structure(self) -> None:
        """Test parsing with invalid response structure."""
        parser = GraphQLResponseParser()

        invalid_response = {"invalid": "structure"}

        with pytest.raises(ValueError) as exc_info:
            parser.parse_review_threads_response(invalid_response)
        assert "Response missing 'data' field" in str(exc_info.value)

    def test_parse_single_review_thread_with_multiple_comments(self) -> None:
        """Test parsing a thread with multiple comments."""
        parser = GraphQLResponseParser()

        thread_data = {
            "id": "RT_multi",
            "isResolved": False,
            "comments": {
                "nodes": [
                    {
                        "id": "IC_1",
                        "body": "Original comment",
                        "createdAt": "2024-01-15T10:00:00Z",
                        "updatedAt": "2024-01-15T10:00:00Z",
                        "author": {"login": "author1"},
                        "replyTo": None,
                    },
                    {
                        "id": "IC_2",
                        "body": "Reply to original",
                        "createdAt": "2024-01-15T11:00:00Z",
                        "updatedAt": "2024-01-15T11:00:00Z",
                        "author": {"login": "author2"},
                        "replyTo": {"id": "IC_1"},
                    },
                ]
            },
        }

        thread = parser._parse_single_review_thread(thread_data)

        assert thread.thread_id == "RT_multi"
        assert thread.title == "Original comment"
        assert thread.author == "author1"
        assert len(thread.comments) == 2

        # Check comment relationships
        original_comment = thread.comments[0]
        reply_comment = thread.comments[1]

        assert original_comment.parent_id is None
        assert reply_comment.parent_id == "IC_1"

    def test_parse_single_review_thread_no_comments(self) -> None:
        """Test parsing thread with no comments raises error."""
        parser = GraphQLResponseParser()

        thread_data = {"id": "RT_empty", "isResolved": False, "comments": {"nodes": []}}

        with pytest.raises(ValueError) as exc_info:
            parser._parse_single_review_thread(thread_data)
        assert "has no comments" in str(exc_info.value)

    def test_parse_single_comment_basic(self) -> None:
        """Test parsing a basic comment."""
        parser = GraphQLResponseParser()

        comment_data = {
            "id": "IC_test",
            "body": "Test comment body",
            "createdAt": "2024-01-15T10:30:00Z",
            "updatedAt": "2024-01-15T10:30:00Z",
            "author": {"login": "testuser"},
            "replyTo": None,
        }

        comment = parser._parse_single_comment(comment_data, "RT_test")

        assert comment.comment_id == "IC_test"
        assert comment.content == "Test comment body"
        assert comment.author == "testuser"
        assert comment.thread_id == "RT_test"
        assert comment.parent_id is None
        assert isinstance(comment.created_at, datetime)
        assert isinstance(comment.updated_at, datetime)

    def test_parse_single_comment_with_reply(self) -> None:
        """Test parsing a comment that's a reply."""
        parser = GraphQLResponseParser()

        comment_data = {
            "id": "IC_reply",
            "body": "This is a reply",
            "createdAt": "2024-01-15T11:00:00Z",
            "updatedAt": "2024-01-15T11:00:00Z",
            "author": {"login": "replyer"},
            "replyTo": {"id": "IC_original"},
        }

        comment = parser._parse_single_comment(comment_data, "RT_test")

        assert comment.comment_id == "IC_reply"
        assert comment.parent_id == "IC_original"

    def test_parse_single_comment_missing_author(self) -> None:
        """Test parsing comment with missing author info."""
        parser = GraphQLResponseParser()

        comment_data = {
            "id": "IC_no_author",
            "body": "Comment without author",
            "createdAt": "2024-01-15T10:30:00Z",
            "updatedAt": "2024-01-15T10:30:00Z",
        }

        comment = parser._parse_single_comment(comment_data, "RT_test")

        assert comment.author == "unknown"

    def test_extract_title_from_comment_normal(self) -> None:
        """Test extracting title from normal comment."""
        parser = GraphQLResponseParser()

        content = "This is a single line comment"
        title = parser._extract_title_from_comment(content)

        assert title == "This is a single line comment"

    def test_extract_title_from_comment_multiline(self) -> None:
        """Test extracting title from multiline comment."""
        parser = GraphQLResponseParser()

        content = "First line of comment\nSecond line\nThird line"
        title = parser._extract_title_from_comment(content)

        assert title == "First line of comment"

    def test_extract_title_from_comment_long(self) -> None:
        """Test extracting title from very long comment."""
        parser = GraphQLResponseParser()

        content = "x" * 150  # Very long content
        title = parser._extract_title_from_comment(content)

        assert len(title) == 100  # Should be truncated to 100 chars
        assert title.endswith("...")

    def test_extract_title_from_comment_empty(self) -> None:
        """Test extracting title from empty comment."""
        parser = GraphQLResponseParser()

        title = parser._extract_title_from_comment("")
        assert title == "Empty comment"

        title = parser._extract_title_from_comment("   \n  \t  ")
        assert title == "Empty comment"

    def test_parse_paginated_response_with_next_page(self) -> None:
        """Test parsing paginated response with next page."""
        parser = GraphQLResponseParser()

        response = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "pageInfo": {
                                "hasNextPage": True,
                                "endCursor": "Y3Vyc29yOnYyOpHOBZnKHA==",
                            },
                            "nodes": [
                                {
                                    "id": "RT_page1",
                                    "isResolved": False,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "id": "IC_page1",
                                                "body": "Page 1 comment",
                                                "createdAt": "2024-01-15T10:30:00Z",
                                                "updatedAt": "2024-01-15T10:30:00Z",
                                                "author": {"login": "user1"},
                                                "replyTo": None,
                                            }
                                        ]
                                    },
                                }
                            ],
                        }
                    }
                }
            }
        }

        threads, next_cursor = parser.parse_paginated_response(response)

        assert len(threads) == 1
        assert threads[0].thread_id == "RT_page1"
        assert next_cursor == "Y3Vyc29yOnYyOpHOBZnKHA=="

    def test_parse_paginated_response_last_page(self) -> None:
        """Test parsing paginated response on last page."""
        parser = GraphQLResponseParser()

        response = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [
                                {
                                    "id": "RT_last",
                                    "isResolved": True,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "id": "IC_last",
                                                "body": "Last page comment",
                                                "createdAt": "2024-01-15T12:00:00Z",
                                                "updatedAt": "2024-01-15T12:00:00Z",
                                                "author": {"login": "user2"},
                                                "replyTo": None,
                                            }
                                        ]
                                    },
                                }
                            ],
                        }
                    }
                }
            }
        }

        threads, next_cursor = parser.parse_paginated_response(response)

        assert len(threads) == 1
        assert threads[0].thread_id == "RT_last"
        assert next_cursor is None


class TestResponseValidator:
    """Test the ResponseValidator class."""

    def test_validate_graphql_response_valid(self) -> None:
        """Test validation of valid GraphQL response."""
        response = {
            "data": {"repository": {"pullRequest": {"reviewThreads": {"nodes": []}}}}
        }

        assert ResponseValidator.validate_graphql_response(response) is True

    def test_validate_graphql_response_not_dict(self) -> None:
        """Test validation fails for non-dictionary response."""
        with pytest.raises(ValueError) as exc_info:
            ResponseValidator.validate_graphql_response("not a dict")
        assert "must be a dictionary" in str(exc_info.value)

    def test_validate_graphql_response_missing_data(self) -> None:
        """Test validation fails when data field is missing."""
        response = {"errors": []}

        with pytest.raises(ValueError) as exc_info:
            ResponseValidator.validate_graphql_response(response)
        assert "missing 'data' field" in str(exc_info.value)

    def test_validate_graphql_response_with_errors(self) -> None:
        """Test validation handles GraphQL errors."""
        response = {
            "errors": [{"message": "Field not found"}, {"message": "Invalid argument"}]
        }

        with pytest.raises(ValueError) as exc_info:
            ResponseValidator.validate_graphql_response(response)
        assert "GraphQL errors" in str(exc_info.value)
        assert "Field not found" in str(exc_info.value)

    def test_validate_graphql_response_null_repository(self) -> None:
        """Test validation fails when repository is null."""
        response = {"data": {"repository": None}}

        with pytest.raises(ValueError) as exc_info:
            ResponseValidator.validate_graphql_response(response)
        assert "Repository not found" in str(exc_info.value)

    def test_validate_graphql_response_null_pull_request(self) -> None:
        """Test validation fails when pull request is null."""
        response = {"data": {"repository": {"pullRequest": None}}}

        with pytest.raises(ValueError) as exc_info:
            ResponseValidator.validate_graphql_response(response)
        assert "Pull request not found" in str(exc_info.value)

    def test_validate_review_thread_data_valid(self) -> None:
        """Test validation of valid review thread data."""
        thread_data = {"id": "RT_test", "isResolved": False, "comments": {"nodes": []}}

        assert ResponseValidator.validate_review_thread_data(thread_data) is True

    def test_validate_review_thread_data_missing_id(self) -> None:
        """Test validation fails when thread ID is missing."""
        thread_data = {"isResolved": False}

        with pytest.raises(ValueError) as exc_info:
            ResponseValidator.validate_review_thread_data(thread_data)
        assert "Missing required field 'id'" in str(exc_info.value)

    def test_validate_review_thread_data_invalid_comments(self) -> None:
        """Test validation fails when comments structure is invalid."""
        thread_data = {"id": "RT_test", "comments": {"invalid": "structure"}}

        with pytest.raises(ValueError) as exc_info:
            ResponseValidator.validate_review_thread_data(thread_data)
        assert "Missing 'nodes' in comments data" in str(exc_info.value)

    def test_validate_comment_data_valid(self) -> None:
        """Test validation of valid comment data."""
        comment_data = {
            "id": "IC_test",
            "body": "Test comment",
            "createdAt": "2024-01-15T10:30:00Z",
            "updatedAt": "2024-01-15T10:30:00Z",
            "author": {"login": "test"},
        }

        assert ResponseValidator.validate_comment_data(comment_data) is True

    def test_validate_comment_data_missing_fields(self) -> None:
        """Test validation fails when required fields are missing."""
        required_fields = ["id", "body", "createdAt", "updatedAt"]

        for missing_field in required_fields:
            comment_data = {
                "id": "IC_test",
                "body": "Test comment",
                "createdAt": "2024-01-15T10:30:00Z",
                "updatedAt": "2024-01-15T10:30:00Z",
            }
            # Remove one required field
            del comment_data[missing_field]

            with pytest.raises(ValueError) as exc_info:
                ResponseValidator.validate_comment_data(comment_data)
            assert f"Missing required field '{missing_field}'" in str(exc_info.value)


class TestParserIntegration:
    """Integration tests for parser functionality."""

    def test_parse_complex_thread_structure(self) -> None:
        """Test parsing a complex thread with nested replies."""
        parser = GraphQLResponseParser()

        response = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [
                                {
                                    "id": "RT_complex",
                                    "isResolved": False,
                                    "comments": {
                                        "nodes": [
                                            {
                                                "id": "IC_1",
                                                "body": "Initial review comment",
                                                "createdAt": "2024-01-15T10:00:00Z",
                                                "updatedAt": "2024-01-15T10:00:00Z",
                                                "author": {"login": "reviewer1"},
                                                "replyTo": None,
                                            },
                                            {
                                                "id": "IC_2",
                                                "body": "Thanks for the feedback!",
                                                "createdAt": "2024-01-15T11:00:00Z",
                                                "updatedAt": "2024-01-15T11:00:00Z",
                                                "author": {"login": "author1"},
                                                "replyTo": {"id": "IC_1"},
                                            },
                                            {
                                                "id": "IC_3",
                                                "body": "More specific guidance...",
                                                "createdAt": "2024-01-15T12:00:00Z",
                                                "updatedAt": "2024-01-15T12:30:00Z",
                                                "author": {"login": "reviewer1"},
                                                "replyTo": {"id": "IC_2"},
                                            },
                                        ]
                                    },
                                }
                            ],
                        }
                    }
                }
            }
        }

        threads, next_cursor = parser.parse_paginated_response(response)

        assert len(threads) == 1
        thread = threads[0]

        # Verify thread properties
        assert thread.thread_id == "RT_complex"
        assert thread.title == "Initial review comment"
        assert thread.status == "UNRESOLVED"
        assert thread.author == "reviewer1"
        assert next_cursor is None

        # Verify comments
        assert len(thread.comments) == 3

        # Verify comment relationships
        initial_comment = thread.comments[0]
        author_reply = thread.comments[1]
        reviewer_followup = thread.comments[2]

        assert initial_comment.parent_id is None
        assert author_reply.parent_id == "IC_1"
        assert reviewer_followup.parent_id == "IC_2"

        # Verify updated_at is the latest
        assert thread.updated_at == reviewer_followup.updated_at

    def test_parse_empty_response(self) -> None:
        """Test parsing response with no review threads."""
        parser = GraphQLResponseParser()

        response = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "reviewThreads": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [],
                        }
                    }
                }
            }
        }

        threads = parser.parse_review_threads_response(response)
        assert len(threads) == 0

        threads, next_cursor = parser.parse_paginated_response(response)
        assert len(threads) == 0
        assert next_cursor is None
