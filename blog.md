---
layout: articles
title: My Blog Posts
permalink: /blog.html
cover: /images/1424006.jpg
mode: immersive

header: 
  theme: dark

article_header: 
  type: overlay
  theme: dark
  background_color: '#123'
  background_image: 
    gradient: 'linear-gradient(135deg, rgba(34, 139, 34, .4), rgba(139, 34, 139, .4))'


# the article settings
articles:
  data_source: site.posts
  type: item
  size: md
  article_type: BlogPosting # the only option
  show_cover: true
  cover_size: lg
  show_excerpt: true
  excerpt_type: text
  show_readmore: false
  show_info: true

# layout: articles
# title: Test with moltiple projects
# cover: /texture.jpg
# articles:
#   data_source: site.longs
#   show_excerpt: true
#   show_readmore: true
#   show_info: true

# layout: "article"
# titles:
#   # @start locale config
#   en      : &EN       Test
#   en-GB   : *EN
#   en-US   : *EN
#   en-CA   : *EN
#   en-AU   : *EN
#   fr      : &FR       Teste
#   fr-BE   : *FR
#   fr-CA   : *FR
#   fr-CH   : *FR
#   fr-FR   : *FR
#   fr-LU   : *FR
#   fa      : &FA       تست
#   # @end locale config
# key: page-123 
---

<div class="layout--archive js-all">
  {%- include tags.html -%}
  <div class="js-result layout--archive__result d-none">
    {%- include article-list.html articles=site.posts type='item' show_info=true reverse=true group_by='year' -%}
  </div>
</div>

Hi
<!-- <div class="article__content" markdown="1"> -->

I time to time write things in my blog. You can access them here. 

<!--more-->

# the desired structure
A list of posts, sorted by date, with some excerpt and pagination.

<!-- </div> -->
