# WSJT-X/JTDX to HamClock DX Interface

![image](https://github.com/user-attachments/assets/6fdef135-ff61-4b06-9dc3-f6551a2b21ea)


This Python application provides an interface between WSJT-X/JTDX and HamClock, automatically looking up callsigns grids at QRZ.com and updating DX information on HamClock. Created by PY2UBK.

## Features

- Real-time monitoring of WSJT-X/JTDX UDP messages
- Automatic callsign lookup via QRZ.com XML API
- Integration with HamClock for grid square updates
- Configurable settings with persistent storage

## Requirements

To run from source:
- Python 3.6 or higher
- WSJT-X or JTDX running on the local network
- QRZ.com subscription (for XML data access)
- HamClock instance running (local or remote)

To run the executable:
- Windows operating system
- WSJT-X or JTDX running on the local network
- QRZ.com subscription
- HamClock instance running

## Installation

### Option 1: Running the Executable (Windows 11)
1. Download the `wsjt-qrz-gui.exe` from the [releases page](https://github.com/boriskauffmann/wsjt2hamclock/releases/tag/v0.1.0)
2. Place it in any directory
3. Run the executable

### Option 2: Running from Source

#### Installing Python on Windows

1. Download Python:
   - Go to [Python Downloads](https://www.python.org/downloads/)
   - Click "Download Python 3.11" (or latest version)
   - Important: Check "Add Python.exe to PATH" during installation!

2. Verify Installation:
   - Open Command Prompt (Windows+R, type "cmd", press Enter)
   - Type: `python --version`
   - Should show Python version number

#### Installing Required Dependencies

1. Open Command Prompt and run:
```bash
pip install requests
```
2. Download the source code "wsjt_qrz_gui.py"
   
3. Install required dependency:
```bash
pip install requests
```
4. Run the application:
```bash
python wsjt_qrz_gui.py
```

## Configuration

On first run, you'll need to configure:

1. HamClock API Endpoint:
   - Default: http://localhost:8080
   - Change to your HamClock's address if running remotely

2. Multicast Group & Port:
   - Default WSJT-X: 224.0.0.1:2237
   - Default JTDX: 224.0.0.1:2237
   - Verify these settings in your WSJT-X/JTDX configuration

3. QRZ Credentials:
   - Your QRZ.com XML API username
   - Your QRZ.com XML API password

Settings are automatically saved to `config.json` for future use.

## Usage

1. Configure your settings and click "Save Settings"
2. Click "Start" to begin monitoring
3. The application will:
   - Monitor WSJT-X/JTDX messages
   - Lookup callsigns on QRZ.com
   - Update HamClock with DX information
   - Display a history of lookups in the main window

## Troubleshooting

1. Check WSJT-X/JTDX Network Settings:
   - Verify the UDP port matches
   - Ensure multicast group address is correct

2. QRZ Lookup Issues:
   - Verify your QRZ.com credentials
   - Ensure you have XML API access

3. HamClock Connection:
   - Verify HamClock is running
   - Check the API endpoint URL
   - Ensure no firewall blocking

4. UDP Reception:
   - Check if your firewall allows UDP traffic
   - Verify the correct multicast group and port settings

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Thanks to the WSJT-X/JTDX developers for their UDP protocol documentation
- Thanks to QRZ.com for their XML API service
- Thanks to the HamClock project for their API integration

## Support

For issues, questions, or suggestions:
1. Open an issue on GitHub
2. Contact PY2UBK
