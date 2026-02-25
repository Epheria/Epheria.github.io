---
title: "Unity iOS - Xcode Code Signing Guide (Certificates & Provisioning Profile)"
date: 2024-05-03 10:00:00 +/-TTTT
categories: [Unity, Build]
tags: [Unity, Build, Xcode, Code Signing, Certificates, Provisioning Profile, iOS]
lang: en
difficulty: intermediate
toc: true
math: true
mermaid: true
---

## Table of Contents
> [Apple Certificate](#apple-certificates)      
> [How to Create App ID (Identifier)](#how-to-create-app-id-identifier)     
> [How to Register Devices](#how-to-register-devices)     
> [How to Create Provisioning Profile](#how-to-create-provisioning-profile)  

<br>
<br>

## Apple Certificates

- To run software (apps, programs) on Apple devices (hardware), a verification process confirms whether the app has been certified by Apple every time it runs.
- Since requesting and managing this every time is cumbersome, obtaining a certificate from [Apple Developer](https://developer.apple.com/account) grants you permission to run apps as a trusted developer.

<br>

## How to Get a Certificate

#### 1. Create a Key (Certificate Signing Request)

![Desktop View](/assets/img/post/unity/ioscodesigning01.png){: : width="800" .normal }

- First, open **Keychain Access** by searching with `Cmd + Space` or navigating to Applications - Utilities - Keychain Access.

<br>

- In **Keychain Access**, you must first create a **CSR (Certificate Signing Request)**.

![Desktop View](/assets/img/post/unity/ioscodesigning02.png){: : width="800" .normal }

- From the top menu, click **Keychain Access -> Certificate Assistant -> Request a Certificate From a Certificate Authority**.

<br>

- **Requesting a Certificate from a Certificate Authority** performs the following:
> 1. Automatically generates a **Public Key** and **Private Key** for the certificate. These keys can be found in the "Keys" category of the Keychain app. (Keep them safe!)      
> ![Desktop View](/assets/img/post/unity/ioscodesigning05.png){: : width="500" .normal }       
> 2. Creates a **CertificateSigningRequest.certSigningRequest** file to send to Apple. This file contains your name, email, and public key, and is signed using your private key.

<br>

![Desktop View](/assets/img/post/unity/ioscodesigning03.png){: : width="600" .normal }

![Desktop View](/assets/img/post/unity/ioscodesigning04.png){: : width="500" .normal }

- After this process, you will see the generated Public and Private keys under the "Keys" section in Keychain Access with the common name you provided.

<br>
<br>

#### 2. Issuing a Certificate

- Go to [Apple Developer](https://developer.apple.com/account) -> Click **Certificates**.

![Desktop View](/assets/img/post/unity/ioscodesigning06.png){: : width="800" .normal }

<br>

---

![Desktop View](/assets/img/post/unity/ioscodesigning07.png){: : width="800" .normal }

- You will see the Certificates, Identifiers & Profiles tab.
- From the left tab, you can create Certificates, Identifiers, Profiles, or register test Devices.
- Click the "+" button to create a Certificate first.

<br>

---

- Generally, iOS Certificates are divided into **Development** and **Distribution**, excluding Enterprise.
> [Difference between Apple Developer Program (Release) and Apple Developer Enterprise Program (In-house Test)](https://developer.apple.com/support/roles/)      
> In summary, **Apple Developer Program** is for App Store releases, and **Enterprise** is for internal company testing.      
> Of course, you can still test via TestFlight by creating a Development Certificate in the Apple Developer Program! (It's not strictly for release only.)

<br>

- The differences between Enterprise and Developer (Release) when creating a Certificate are as follows:

![Desktop View](/assets/img/post/unity/ioscodesigning22.png){: : width="800" .normal }

_Apple Developer Enterprise Program_

![Desktop View](/assets/img/post/unity/ioscodesigning23.png){: : width="800" .normal }

_Apple Developer Program_

<br>

---

- Note that only the Apple Developer Program distinguishes between Development and Distribution.

![Desktop View](/assets/img/post/unity/ioscodesigning10.png){: : width="800" .normal }

<br>

---

- Upload the CSR (CertificateSigningRequest) you created and proceed by clicking Continue.

![Desktop View](/assets/img/post/unity/ioscodesigning11.png){: : width="800" .normal }

<br>

---

- Download the generated Certificate and **double-click** it to automatically register it to your Keychain.

![Desktop View](/assets/img/post/unity/ioscodesigning12.png){: : width="800" .normal }


![Desktop View](/assets/img/post/unity/ioscodesigning13.png){: : width="800" .normal }

- Completing these steps makes you an Apple-certified developer.
- However, you only have permission to sign apps; you still need to verify that the device trusts you as a developer.
- You need to link the newly created Certificate with an iOS device. This is called a **Provisioning Profile**.

<br>
<br>

---

## Provisioning Profile

- A Provisioning Profile contains App ID, Certificate, and Device information, linking iOS devices with the Apple Certificate.

![Desktop View](/assets/img/post/unity/ioscodesigning14.png){: : width="800" .normal }

- 1. **App ID**: Contains the Bundle ID information registered in the App Store.
- 2. **Certificate**: Use the certificate created above when making the Identifier -> Use that Identifier when creating the Provisioning Profile.
- 3. **Device**: UDID of the device to be used for testing.

- Before creating a Provisioning Profile, you need to register an App ID (Identifier) and Devices based on the Certificate.
- First, let's create an App ID.

<br>

---

#### How to Create App ID (Identifier)

- Click **Identifiers** on the left tab -> Click the "+" button to start creating an App ID.

![Desktop View](/assets/img/post/unity/ioscodesigning15.png){: : width="800" .normal }

<br>

---

- Select **App IDs** and click Continue.

![Desktop View](/assets/img/post/unity/ioscodesigning16.png){: : width="800" .normal }

<br>

---

- Select the desired type (App, App Clip) - here we choose **App**.
- Note: Enterprise does not have this step.

![Desktop View](/assets/img/post/unity/ioscodesigning17.png){: : width="800" .normal }

<br>

---

- Specify what this profile is for in **Description** and enter the **Bundle ID**.
- Apple's recommended naming convention is:
> We recommend using a reverse-domain name style string (i.e., com.domainname.appname). It cannot contain an asterisk (*).

![Desktop View](/assets/img/post/unity/ioscodesigning18.png){: : width="800" .normal }

<br>

---

- Make sure to check the **Capabilities** you will use. (Can be modified later)
- Commonly used ones include **Push Notifications** and **Sign in with Apple**. (Often forgotten during initial setup)

![Desktop View](/assets/img/post/unity/ioscodesigning19.png){: : width="800" .normal }

- Click Continue and then Register to register the App ID in Identifiers!

<br>

---

#### How to Register Devices

- Click **Devices** -> Click the "+" button to register a device.

![Desktop View](/assets/img/post/unity/ioscodesigning20.png){: : width="800" .normal }

<br>

---

- For **Device Name**, it's better to use a name like the device type or model.
- **UDID** is the unique device ID, which can be found in settings (or via Finder/iTunes).

![Desktop View](/assets/img/post/unity/ioscodesigning21.png){: : width="800" .normal }

<br>

---

#### How to Create Provisioning Profile

- Now that everything (Certificate, App ID, Device) is ready, we need to make the Provisioning Profile.
- Click **Profiles** -> Click "+" to start creating a Provisioning Profile.

![Desktop View](/assets/img/post/unity/ioscodesigning24.png){: : width="800" .normal }

<br>

---

- Differences between Enterprise and Developer (Release) when creating a Provisioning Profile:

![Desktop View](/assets/img/post/unity/ioscodesigning08.png){: : width="800" .normal }

_Apple Developer Enterprise Program_

![Desktop View](/assets/img/post/unity/ioscodesigning09.png){: : width="800" .normal }

_Apple Developer Program_

<br>

- Note: **Ad Hoc** allows distribution by registering internal testers, and **In House** allows distribution by registering the .ipa file to services like App Center.

<br>

---

- Select Development or Distribution and click Continue.

![Desktop View](/assets/img/post/unity/ioscodesigning25.png){: : width="800" .normal }

<br>

---

- Select the **App ID** you just created and click Continue.

![Desktop View](/assets/img/post/unity/ioscodesigning26.png){: : width="800" .normal }

<br>

---

- Select the **Certificate** created earlier and click Continue.

![Desktop View](/assets/img/post/unity/ioscodesigning27.png){: : width="800" .normal }

<br>

---

- Select the **Device** and...

![Desktop View](/assets/img/post/unity/ioscodesigning28.png){: : width="800" .normal }

<br>

---

- Enter a **Provisioning Profile Name** and click **Generate** to create it.

![Desktop View](/assets/img/post/unity/ioscodesigning29.png){: : width="800" .normal }

<br>

---

- Download the Provisioning Profile and place it inside your Unity Project!
- For Toyverse, we organized folders under a `Keystore` folder separated by Development, Enterprise, and App Store.

![Desktop View](/assets/img/post/unity/ioscodesigning31.png){: : width="500" .normal }

<br>

---

- Each folder contains the Certificate and Provisioning Profile.

![Desktop View](/assets/img/post/unity/ioscodesigning30.png){: : width="800" .normal }

<br>

---

- The reason for placing the Provisioning Profile here is that when building the Unity project and exporting to Xcode, checking **Automatically Manage Signing** allows you to register it in Project Settings / Preferences. For details, refer to the [Xcode Build Pipeline Post](https://epheria.github.io/posts/UnityXcodeBuildPipeline/).

![Desktop View](/assets/img/post/unity/ioscodesigning32.png){: : width="800" .normal }

- This completes the Code Signing process!

<br>

---

- If an error occurs, check if the **Bundle Identifier** is correct!
- Since you can have multiple Provisioning Profiles, the linked App ID must match the Bundle ID of the project you are trying to compile.
