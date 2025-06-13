<h1 align="center"> ──「🎵 TEAM x MUSIC 2.0 」──</h1>

<p align="center">
  <img src="https://files.catbox.moe/hxzqbf.jpg" alt="TeamX Music Logo" width="600" height="400">
</p>

<h3 align="center">Delivering Superior Music Experience to Telegram</h3>

<p align="center">
  <a href="https://t.me/TeamsXchat"><img src="https://img.shields.io/badge/Support-Group-blue?style=for-the-badge&logo=telegram"></a>
  <a href="https://t.me/TeamXUpdate"><img src="https://img.shields.io/badge/Updates-Channel-blue?style=for-the-badge&logo=telegram"></a>
  <a href="https://github.com/strad-dev131/TeamXmusic2.0/blob/main/LICENSE"><img src="https://img.shields.io/github/license/informasgher89745/TeamX2?style=for-the-badge"></a>
</p>

---

## 📚 Table of Contents

- [🛠 YouTube Fix](#-youtube-fix)
- [🌟 Features](#-features)
- [🚀 Deploy on Heroku](#-deploy-on-heroku)
- [⚙️ Quick Setup](#️-quick-setup)
- [🛠 Commands & Usage](#-Commands-Usage)
- [🔄 Updates & Support](#-updates--support)
- [🤝 Contributing](#-contributing)
- [📜 License](#-license)
- [🙏 Acknowledgements](#-acknowledgements)

---

## 🛠 YouTube Fix

Due to YouTube blocking VPS IPs, we’ve implemented a workaround:

1. **Join the [Support Group](https://t.me/TeamsXchat)** and type `#script` to get the script.
2. **Run the script** on your Windows desktop via VS Code (or similar) to generate cookies.
3. **Fork this repository**.
4. **Paste the cookies** into the `cookies/` folder.
5. **Deploy** the bot as shown in the instructions below.

This bypass ensures smooth music playback even with YouTube restrictions.

---

## 🌟 Features

- 🎧 **Multi-Source Streaming** – Play from YouTube, Telegram, and more.
- 🎶 **Queue Support** – Add multiple tracks for seamless listening.
- 🔁 **Playback Controls** – Skip, pause, resume, repeat, and shuffle.
- 📢 **High-Quality Audio** – Crystal-clear sound output.
- ⚙️ **Custom Settings** – Equalizer, volume control, and more.

---

## 🚀 Deploy on Heroku

Click the button below to deploy the bot on Heroku instantly:

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://dashboard.heroku.com/new?template=https://github.com/strad-dev131/TeamXmusic2.0)

---

### 🔧 Quick Setup

1. **Upgrade & Update:**
   ```bash
   sudo apt-get update && sudo apt-get upgrade -y
   ```

2. **Install Required Packages:**
   ```bash
   sudo apt-get install python3-pip ffmpeg -y
   ```
3. **Setting up PIP**
   ```bash
   sudo pip3 install -U pip
   ```
4. **Installing Node**
   ```bash
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash && source ~/.bashrc && nvm install v18
   ```
5. **Clone the Repository**
   ```bash
   git clone https://github.com/strad-dev131/TeamXmusic && cd TeamXmusic
   ```
6. **Install Requirements**
   ```bash
   pip3 install -U -r requirements.txt
   ```
7. **Create .env  with sample.env**
   ```bash
   cp sample.env .env
   ```
   - Edit .env with your vars
8. **Editing Vars:**
   ```bash
   vi .env
   ```
   - Edit .env with your values.
   - Press `I` button on keyboard to start editing.
   - Press `Ctrl + C`  once you are done with editing vars and type `:wq` to save .env or `:qa` to exit editing.
9. **Installing tmux**
    ```bash
    sudo apt install tmux -y && tmux
    ```
10. **Run the Bot**
    ```bash
    bash start
    ```

---

### 🛠 Commands & Usage

The TeamX Music Bot offers a range of commands to enhance your music listening experience on Telegram:

| Command                 | Description                                 |
|-------------------------|---------------------------------------------|
| `/play <song name>`     | Play the requested song.                    |
| `/pause`                | Pause the currently playing song.           |
| `/resume`               | Resume the paused song.                     |
| `/skip`                 | Move to the next song in the queue.         |
| `/stop`                 | Stop the bot and clear the queue.           |
| `/queue`                | Display the list of songs in the queue.     |

For a full list of commands, use `/help` in [telegram](https://t.me/sidduXMusicBot).

---

### 🔄 Updates & Support

Stay updated with the latest features and improvements to TeamX Music Bot:

<p align="center">
  <a href="https://t.me/TeamsXchat">
    <img src="https://img.shields.io/badge/Join-Support%20Group-blue?style=for-the-badge&logo=telegram">
  </a>
  <a href="https://t.me/TeamXUpdate">
    <img src="https://img.shields.io/badge/Join-Update%20Channel-blue?style=for-the-badge&logo=telegram">
  </a>
</p>

---

### 🤝 Contributing

We welcome contributions to the TeamX Music Bot project. If you'd like to contribute, please follow these steps:

1. Fork the repository.
2. Create a new branch with a meaningful name.
3. Make your changes and commit them with a descriptive commit message.
4. Open a pull request against our `main` branch.
5. Our team will review your changes and provide feedback.

For more details, reach out us on telegram.

---

### 📜 License

This project is licensed under the MIT License. For more details, see the [LICENSE](LICENSE) file.

---

### 🙏 Acknowledgements

Thanks to all the contributors, supporters, and users of the TeamX Music Bot. Your feedback and support keep us going!

