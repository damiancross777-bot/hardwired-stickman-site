# Episode content schema

Each file in `content/episodes/` represents one video and one website article.

## Required publishing fields

- `title`
- `slug`
- `status`: `draft` or `published`
- `published_at`: ISO 8601 with timezone
- `category`: normally `Human Behaviour` or `Animal Behaviour`
- `summary`
- `answer`
- `youtube_url`
- `youtube_id`
- `duration_iso`: ISO 8601 duration such as `PT8M30S`
- `thumbnail_url`
- `key_findings`
- `article_markdown`
- `sources`
- `seo`
- `pinterest`
- `instagram`

## Draft behaviour

Draft episodes are ignored by the public site and social generator.

## Sources

Use complete, publicly accessible URLs. Prefer primary research, systematic reviews, government sources, university publications and established scientific outlets.

Remove all placeholder sources before publishing.
