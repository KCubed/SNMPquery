
# This program is designed to search arista or cisco switches and determine if a VLAN already exists. It is limited
# to using SNMP through a jump server.

import paramiko
import time
import pingparsing
import getpass


def pingCheck(str):
    transmitter = pingparsing.PingTransmitter()
    transmitter.destination_host = line
    results = transmitter.ping()
    return(results.returncode)

def findVendor(str):
    #this uses SSH, SNMP is preferred.
    if "cisco" in str.lower():
        vendor = "Cisco"
    elif "arista" in str.lower():
        vendor = "Arista"
    elif "junos" in str.lower():
        vendor = "Juniper"
    else:
        vendor = "unknown"
    return(vendor)

def snmpSysInfo():
    remote_connection.send("snmpget -v 2c -c " + communityRO + " " + line.rstrip() + " sysDescr.0\n")
    # Wait for commands to complete
    time.sleep(2)

def queryCisco():
    remote_connection.send(
        "snmpwalk -v 2c -c " + communityRO + " " + line.rstrip() + " 1.3.6.1.4.1.9.9.46.1.3.1.1.4.1 | grep 156\n")
    # Wait for commands to complete
    time.sleep(2)

def queryArista():
    remote_connection.send(
        "snmpwalk -v 2c -c " + communityRO + " " + line.rstrip() + " mib-2.17.7.1.4.3.1.1 | grep 156\n")
    # Wait for commands to complete
    time.sleep(2)

def writeDebug():
    output = remote_connection.recv(65535)
    formatOutput = bytes(str(output), "utf-8").decode("unicode_escape")
    debugFile.write(str(formatOutput))
    return(str(formatOutput))

def writeSysInfo(formatOutput):
    if "snmpv2-mib::sysdescr.0" in formatOutput.lower():
        deviceInfo = formatOutput.split("SNMPv2-MIB::sysDescr.0 = STRING: ")[1]
        #limit to 148 chars to avoid excess info
        deviceInfo = deviceInfo[:148]
        deviceInfo = deviceInfo.split("-bash-2.05b$")[0]
        #strip carrage returns
        resultsFile.write(line.rstrip() + ", " + deviceInfo.replace('\n', ' ') + ". \n")

def writeCisco(outputFormatted):
    if "string: " in outputFormatted.lower():
        vlanFound = outputFormatted.split("STRING: ")[1]
        vlanFound = vlanFound.split("-bash-2.05b$")[0]
        resultsFile.write("VLAN 156 found with name " + vlanFound.rstrip() + ".\n")
    else:
        resultsFile.write("VLAN 156 not found on this device. \n")

def writeArista(outputFormatted):
    if "snmpv2-smi::mib-2.17.7.1.4.3.1.1.156 = string:" in str(outputFormatted).lower():
        vlanFound = str(outputFormatted).split("SNMPv2-SMI::mib-2.17.7.1.4.3.1.1.156 = STRING: ")[1]
        vlanFound = vlanFound.split("-bash-2.05b$")[0]
        resultsFile.write("VLAN 156 found with name " + vlanFound.rstrip() + ".\n")
    else:
        resultsFile.write("VLAN 156 not found on this device. \n")

ssh_client = paramiko.SSHClient()
#Allow for any certs (do not run in production!)
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

#Read in list of device hostnames/IPs
deviceList = open("deviceList.txt", "r")

#Get credentials
nmsServer = input("NMS server: ")
user = input("Username: ")
password = getpass.getpass("Enter your password for " + nmsServer + ": ")
communityRO = getpass.getpass("RO Community: ")

#Connect to NMS server
ssh_client.connect(nmsServer, 22, user, password)
remote_connection = ssh_client.invoke_shell()
print("### SSH session established to " + nmsServer + " ###")

#Save output to file
debugFile = open( nmsServer + "_debug.txt", "w")
resultsFile = open( "results.txt", "w")
resultsFile.write("---------- \n")

#Run SNMP queries
for line in deviceList:
    #Check device is reachable over network
    isItDown = pingCheck(line)

    #iterate through list of devices
    if not isItDown:
        #query device using SNMP for hardware info, record to debug
        print("### Gathering information via SNMP for " + line.rstrip() + " ###")
        snmpSysInfo()
        outputFormatted = writeDebug()

        #parse to determine if the device is cisco, juniper, arista, or other
        vendor = findVendor(outputFormatted)

        #get model/version information and save to results
        writeSysInfo(outputFormatted)
        time.sleep(2)

        # check for VLAN 156
        if vendor == "Cisco":
            queryCisco()
            outputFormatted = writeDebug()
            writeCisco(outputFormatted)
        elif vendor == "Arista":
            queryArista()
            outputFormatted = writeDebug()
            writeArista(outputFormatted)
        elif vendor == "Juniper":
            print("No EX switches are implemented. This must be a router.")
            resultsFile.write(line.rstrip() + ", No VLANs to check for in a Juniper router")
        else:
            print("unknown device")
            resultsFile.write(line.rstrip() + ", unknown device type")
    else:
        print ("### Can't reach " + line.rstrip() + " ###")
        resultsFile.write( line.rstrip() + ", unable to reach " + line.rstrip() + " . \n")
    resultsFile.write("---------- \n")

#Clean up
ssh_client.close()
print ("### SSH session to " + nmsServer + " closed. ###")
debugFile.close()
resultsFile.close()