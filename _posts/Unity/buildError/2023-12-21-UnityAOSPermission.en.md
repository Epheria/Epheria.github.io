---
title: How to Fix Unity Android Permission Not Being Removed Issue
date: 2023-12-21 12:59:00 +/-TTTT
categories: [Unity, Build Error]
tags: [Unity, Build, Jenkins, Automation, Android Permission]
lang: en
difficulty: intermediate
toc: true
---

- **An issue occurred where Unity Android Permission was not being removed.**
- **The `READ_EXTERNAL_STORAGE` permission, which is not even used, kept being included in the build.**

   ![Desktop View](/assets/img/post/unity/unityaosperm01.png){: : width="800" .normal }

<br>

## **Root Cause Analysis**

- First, I checked the `AndroidManifest` file, but there was no usage of that permission.
- I searched the entire project to see where it was being used...

   ![Desktop View](/assets/img/post/unity/unityaosperm04.png){: : width="800" .normal }

   ![Desktop View](/assets/img/post/unity/unityaosperm03.png){: : width="800" .normal }

- I found a Unity package cache file called `PostprocessorTests`, an internal class of `Unity.Notifications.Tests`.
- It turned out this class inside the Mobile Notification package was using that permission.

   ![Desktop View](/assets/img/post/unity/unityaosperm05.png){: : width="800" .normal }

<br>

## **Solution**

1. Check if the permission you want to remove exists in the `AndroidManifest` file. In my case, it was `READ_EXTERNAL_STORAGE`.
2. Use the "Find in Files" feature in your IDE (Rider or Visual Studio) to search for the permission string and verify if it's being used anywhere.

- Permission Example:
```xml
  <uses-permission android:name="android.permission.READ_MEDIA_IMAGES" android:minSdkVersion="33" />
  <uses-permission android:name="android.permission.READ_MEDIA_VIDEO" android:minSdkVersion="33" />
  <uses-permission android:name="android.permission.READ_MEDIA_AUDIO" android:minSdkVersion="33" />
  <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
  <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
```

3. If there is a permission you want to remove, delete it boldly.
4. However, since it might be included in Unity packages or plugins, you must handle it explicitly.

- **You can resolve this by explicitly specifying `remove`.**
```xml
  <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" tools:node="remove" />
```

- Result:
   ![Desktop View](/assets/img/post/unity/unityaosperm02.png){: : width="800" .normal }
