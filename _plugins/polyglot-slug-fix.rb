#!/usr/bin/env ruby
#
# Fix: jekyll-polyglot keeps language suffix in post slugs
# e.g., "ClaudeCodeInsights.en" → "ClaudeCodeInsights"
# This ensures translated posts have clean URLs like
# /en/posts/Slug/ instead of /en/posts/Slug.en/

Jekyll::Hooks.register :posts, :post_init do |post|
  slug = post.data['slug']
  lang = post.data['lang']
  next unless slug && lang

  suffix = ".#{lang}"
  if slug.end_with?(suffix)
    post.data['slug'] = slug.chomp(suffix)
  end
end
