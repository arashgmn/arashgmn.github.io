---
title: Template for post
cover:
key: post-temp
lang:
tag: temp
permalink: 
published: false
---

A post template for blogging.

<!--more-->

# Front Matter
The qunatities in the front matter above must be all filled ideally:

- **cover**: The picture on the top like `/images/<img_name.extension>`. If not specifed, take a default value.
- **key**: It is needed for commenting. You can drop it if you don't want comments.
- **lang**: By default, it assumes that the text is in english. Otherwise provide `fa`
- **tag**: Highly adviced to use! If there are multiple tags, simply change the property name to `tags` and put them in a list like `[tag1,tag2]`.
- **permalink**: It's again recommended. But I'm not sure if it's necessary for my needs.

# Excerpt
The first paragraph before `<!--more-->` will be interpreted as the excerpt. If `<!--more-->` isn't provided, it automatically takes the first block of the text. Keep it short for visual purposes.

# Other considerations
Nothing. Just write and enjoy!

