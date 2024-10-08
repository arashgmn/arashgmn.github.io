---
layout: post
title: Right to left scripting
date: 2022-10-15 
description: you can also write from right to left
lang: fa
tags: internationalization formatting math code
category: internationalization
published: false
---

# عنوان
این یک پست نمونه برای سنجش نوشتارهای راست‌به‌چپ است.


## فرمول‌نویسی
فرمول‌ها هم مانند کد به درستی به نمایش در‌خواهند آمد:


$$
\sum_{k=1}^\infty |\langle x, e_k \rangle|^2 \leq \|x\|^2
$$

## کد
کدها هم‌چنان مانند قبل از چپ‌به‌راست خواهند بود.

```python
if lang=="rtl"
    print("I am a right-to-left script!")
```

## بلاک
بلاک‌ها همواره چپ‌چین خواهند ماند:

    ---
    layout: page
    title: project
    description: a project with a background image
    img: /assets/img/12.jpg
    ---

حتی اگر به زبان‌های راست‌به‌چپ نوشته شوند:

    ---
    صفحه‌بندی: صفحه
    عنوان: پروژه
    توضیحات: یک پروژه با تصویر زمینه
    ---

## نقل‌قول
> نقل‌قول‌ها به این شکل به نمایش درخواهند آمد.
زیباتر خواهد بود اگر خط عمودی به راست انتقال داده شود. این کار با ویرایش _base.scss امکان‌پذیر است:

```scss
blockquote {
  background: var(--global-bg-color);
  border-left: 2px solid var(--global-theme-color); // change to border-right:
  margin: 1.5em 10px;
  padding: 0.5em 10px;
  font-size: 1.2rem;
}
...
.post-content{
  blockquote {
    border-left: 5px solid var(--global-theme-color); // change to border-right: ...
    padding: 8px;
  }
}
```

منطقا باید بتوان با توجه به جهت‌گیری متن (rtl یا ltr) صفت مناسب را تعریف کرد. اما من چندان به sass مسلط نیستم. امیدوارم فرد مسلط‌تری این مشکل کوچک را رفع کند.
