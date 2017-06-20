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

    if not isItDown:
        #get hardware info
        print("### Gathering information via SNMP for " + line.rstrip() + " ###")
        remote_connection.send("snmpget -v 2c -c " + communityRO + " " + line.rstrip() + " sysDescr.0\n")
        #Wait for commands to complete
        time.sleep(2)

        output = remote_connection.recv(65535)
        outputFormatted = bytes(str(output), "utf-8").decode("unicode_escape")
        # save debug file
        debugFile.write(str(outputFormatted))

        vendor = findVendor(str(outputFormatted))

        #get model/version information
        if "snmpv2-mib::sysdescr.0" in str(outputFormatted).lower():
            deviceInfo = str(outputFormatted).split("SNMPv2-MIB::sysDescr.0 = STRING: ")[1]
            deviceInfo = deviceInfo[:148]
            deviceInfo = deviceInfo.split("-bash-2.05b$")[0]
            resultsFile.write(line.rstrip() + ", " + deviceInfo.replace('\n', ' ') + ". \n")
        time.sleep(2)

        # check for VLAN 156
        if vendor == "Cisco":
            remote_connection.send("snmpwalk -v 2c -c " + communityRO + " " + line.rstrip() + " 1.3.6.1.4.1.9.9.46.1.3.1.1.4.1 | grep 156\n")
            # Wait for commands to complete
            time.sleep(2)
            output = remote_connection.recv(65535)
            outputFormatted = bytes(str(output), "utf-8").decode("unicode_escape")
            # save debug file
            debugFile.write(str(outputFormatted))
            if "string: " in str(outputFormatted).lower():
                vlanFound = str(outputFormatted).split("STRING: ")[1]
                vlanFound = vlanFound.split("-bash-2.05b$")[0]
                resultsFile.write("VLAN 156 found with name " + vlanFound.rstrip() + ".\n")
            else:
                resultsFile.write("VLAN 156 not found on this device. \n")
        elif vendor == "Arista":
            remote_connection.send("snmpwalk -v 2c -c " + communityRO + " " + line.rstrip() + " mib-2.17.7.1.4.3.1.1 | grep 156\n")
            # Wait for commands to complete
            time.sleep(2)
            output = remote_connection.recv(65535)
            outputFormatted = bytes(str(output), "utf-8").decode("unicode_escape")
            # save debug file
            debugFile.write(str(outputFormatted))
            if "snmpv2-smi::mib-2.17.7.1.4.3.1.1.156 = string:" in str(outputFormatted).lower():
                vlanFound = str(outputFormatted).split("SNMPv2-SMI::mib-2.17.7.1.4.3.1.1.156 = STRING: ")[1]
                vlanFound = vlanFound.split("-bash-2.05b$")[0]
                resultsFile.write("VLAN 156 found with name " + vlanFound.rstrip() + ".\n")
            else:
                resultsFile.write("VLAN 156 not found on this device. \n")
        elif vendor == "Juniper":
            print("Modify in future when EX switches are implemented.")
            resultsFile.write(line.rstrip() + "No VLANs to check for in a Juniper router")
        else:
            print("unknown device")
            resultsFile.write(line.rstrip() + ", unknown device type")
    else:
        print ("### Can't reach " + line.rstrip() + " ###")
        resultsFile.write( line.rstrip() + ", unable to reach " + line.rstrip() + " . \n")
    resultsFile.write("---------- \n")

#Close SSH connection
ssh_client.close()
print ("### SSH session to " + nmsServer + " closed. ###")


debugFile.close()
resultsFile.close()