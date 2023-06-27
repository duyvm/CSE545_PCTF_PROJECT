# CSE545_PCTF_PROJECT

## About CTF
https://en.wikipedia.org/wiki/Capture_the_flag_(cybersecurity)

## Team Bindevil

Members:

 - Vo Minh Duy, vduy1@asu.edu
 - Kosuke Nagae, knagae@asu.edu
 - Hongbo Wu, hongbowu@asu.edu
 - He Jiang, hjiang81@asu.edu
 - Jinyi Yu, jinyiyu@asu.edu 

## Team Reports

[Here](/reports/)

## [Flag Submission](flag-submit)

This tool automatically submits flag for team. Provide either individual flag or file which stores multiple flags for submission. Change the `TEAM_INTERFACE_IP` and 
`TEAM_FLAG_TOKEN` variables according to team's information before running the script.

```
Usage:

  -s: submit individual flag
  
  -b: specify file which contains multiple flags
  
  -v: view information about our Virtual Machine in PCTF
 ```

Note: run command below to install setuptools on pctf vm before install libraries in requirements.txt

    pip install -U pip setuptools

## [Auto Search Flag](auto-search-flag)

This tool exploits the backup service, find and submit obtained flags automatically.

## [Firewall](onestone-firewall)

This tool sets up the firewall to protect our services from attacks and capture packet for analysis. 

## [Vulnerability scan](vulnerability-scan)

This tool automatically scans defined vulnerabilities in C or PHP file.

## [Auto exploit scripts](auto-exploit-script)

These are all the scripts that the team have developped during the game. Each script targets a specific service. The script automatically exploits the service, obtains flags, filters and submits them to server.

## TIPS

1. Copy file/folder from local to host

    File: 

        scp -i key_file file_dir ctf@xxx.xxx.xxx.xxx:/home/ctf

    Folder: 

        scp -i key_file -r folder_dir ctf@xxx.xxx.xxx.xxx:/home/ctf

2. Set up cron job for executing python script every three minutes

    Add exec permission to script
    ```
    chmod +x /path/to/script
    ```
    Open crontab for editting:
    ```
    crontab -e

    ```
    Add the following line for target script into crontab:
    ```
    3 * * * * /path/to/script arg1 arg2
    ```

