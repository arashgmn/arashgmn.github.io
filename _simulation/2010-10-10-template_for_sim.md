---
title: Template for simulations
cover:
key: sim-temp
lang:
tag: temp
permalink: 
#published: false
---

A simulation template.

<!--more-->

# Front Matter
The qunatities in the front matter above must be all filled ideally:

- **cover**: The picture on the top like `/images/<img_name.extension>`. If not specifed, take a default value.
- **key**: It is needed for commenting. You can drop it if you don't want comments.
- **lang**: By default, it assumes that the text is in english. Otherwise provide `fa`
- **permalink**: It's again recommended. But I'm not sure if it's necessary for my needs.

> **Note**: Using `tag` isn't necessary. There will be only a handful of simulations and easy to search. Plus, I still don't know how to include the simulation tags in the archive page tags.

# Excerpt
The first paragraph before `<!--more-->` will be interpreted as the excerpt. If `<!--more-->` isn't provided, it automatically takes the first block of the text. Keep it short for visual purposes.

# Other considerations
Nothing. Just write and enjoy!

# A test with [Plotly](https://plotly.com/python/)
<iframe id="igraph" scrolling="yes" style="border:none;" seamless="seamless" src="https://plotly.com/~arashgmn/58.embed" height="900" width="100%"></iframe>
