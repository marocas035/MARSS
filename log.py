from spade import quit_spade
import json
import time
import datetime
from datetime import date
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from spade.template import Template
from spade.message import Message
import sys
import pandas as pd
import logging
import argparse
import operative_functions as opf
import os
from os import remove
import logging.handlers as handlers
import re


class LogAgent(Agent):
    class LogBehav(CyclicBehaviour):
        async def run(self):
            global wait_msg_time, logger, log_status_var, active_agents
            if log_status_var =="on":
                "Active Agents"
                r= opf.checkFileExistance()
                if r == True:
                    agent_id = []
                    agent_name = []
                    agent_type = []
                    activation_time = []
                    a = pd.read_csv('ActiveAgents.csv', header=0, delimiter=",", engine='python')
                    if len(a) != 0:
                        for line in a.index:
                            agent_jid = a.loc[line, 'agent_id']
                            alive_agent_msg = opf.alive_agent(agent_jid)
                            await self.send(alive_agent_msg)
                            msg2 = await self.receive(timeout=wait_msg_time)  # wait for a message for 3 seconds
                            if msg2:
                                logger.info(msg2.body)
                                msg2_sender_jid0 = str(msg2.sender)
                                msg2_sender_jid2 = msg2_sender_jid0[:-9]
                                m = msg2.body.split(':')
                                typeaa = opf.aa_type(msg2_sender_jid2)
                                my_list1 = {'agent_id': msg2_sender_jid2, 'agent_name': m[2] , 'agent_type': typeaa, 'activation_time': m[4] }
                                active_agents = active_agents.append(my_list1, ignore_index = True)
                                active_agents = active_agents.drop_duplicates(['agent_id','agent_name'],keep = 'first')
                        remove('ActiveAgents.csv')
                        del a 
                msg = await self.receive(timeout=wait_msg_time)  # wait for a message for 20 seconds
                if msg:
                    print(f"received msg number {self.counter}")
                    self.counter += 1
                    counter = int(self.counter)
                    logger.info(msg.body)
                    msg_sender_jid0 = str(msg.sender)
                    msg_sender_jid = msg_sender_jid0[:-31]
                    msg_sender_jid2 = msg_sender_jid0[:-9]
                    agent_type = opf.aa_type(msg_sender_jid2)
                    time= datetime.datetime.now()
                    """Active agents register"""
                    my_list = [{'agent_id':msg_sender_jid2, 'agent_name': msg_sender_jid, 'agent_type': agent_type,'activation_time': time}]
                    if (counter ==2):
                        active_agents = pd.DataFrame([], columns = ['agent_id', 'agent_name', 'agent_type', 'activation_time'])
                        active_agents = active_agents.append(my_list, ignore_index = True)
                    else:
                        active_agents = active_agents.append(my_list, ignore_index = True)
                        active_agents = active_agents.drop_duplicates(['agent_id','agent_name'],keep = 'first')
                    #print(active_agents)
                    n = f'ActiveAgent: agent_id: agent_id:{msg_sender_jid2}, agent_name:{msg_sender_jid}, type:{agent_type}, active_time:{datetime.datetime.now()}'
                    logger.info(n)
                    """Log file"""
                    fileh = logging.FileHandler(f'{my_dir}/{my_name}.log')
                    formatter = logging.Formatter(f'%(asctime)s;%(levelname)s;{msg_sender_jid2};%(pathname)s;%(message)s')
                    fileh.setFormatter(formatter)
                    log = logging.getLogger()  # root logger
                    for hdlr in log.handlers[:]:  # remove all old handlers
                        log.removeHandler(hdlr)
                    log.addHandler(fileh)
                    if args.verbose == "DEBUG":
                        logger.setLevel(logging.DEBUG)
                    elif args.verbose == "INFO":
                        logger.setLevel(logging.INFO)
                    elif args.verbose == "WARNING":
                        logger.setLevel(logging.WARNING)
                    elif args.verbose == "ERROR":
                        logger.setLevel(logging.ERROR)
                    elif args.verbose == "CRITICAL":
                        logger.setLevel(logging.CRITICAL)
                    else:
                        print('not valid verbosity')
                    msg_2 = pd.read_json(msg.body)
                    if msg_2.loc[0, 'purpose'] == 'inform error':
                        logger.warning(msg.body)
                    elif msg_2.loc[0, 'purpose'] == 'inform change' or 'status' in msg_2:
                        logger.debug(msg.body)
                    elif 'active_coils' in msg_2:
                        logger.critical(msg.body)
                    else:
                        logger.info(msg.body)
                    """Update coil status """
                    x = re.search("won auction to process", msg.body)
                    if x:                                     #update  coil status
                        auction = msg.body.split(" ")
                        coil_id = auction[0]
                        status = auction[6]
                        o = opf.checkFile2Existance()
                        if o == True:
                            opf.update_coil_status(coil_id, status)
                            n = f'Coil: {coil_id} updated status'
                    elif msg_sender_jid == "launcher":
                        single = msg.body.split(':')
                        id = single[4].split('"')
                        if id[3] == 'steel_grade':  #Save order
                            opf.save_order(msg.body)
                            logger.info(msg.body)
                            ackO = "Status: Launcher Order successfully saved"
                            log_msg_la = opf.msg_to_launcher(ackO, my_dir)
                            await self.send(log_msg_la)
                            logger.info(log_msg_la.body)
                    elif msg_sender_jid == "browser":
                        single = msg.body.split(':')
                        aa = single[0].split('"')
                        if aa[0] == 'SearchAA':  #Active agents list requested
                            logger.info(msg.body)
                            list_AA = str(active_agents)
                            log_msg_br = opf.msg_aa_to_br(list_AA, my_dir)
                            await self.send(log_msg_br)                        
                else:
                    logger.debug(f"Log_agent didn't receive any msg in the last {wait_msg_time}s") 
            elif log_status_var == "stand-by":
                print(log_status_var) #### TO DO DEBUG: cambiar formato mensaje 
                logger.debug(f"Log agent status: {log_status_var}")
                log_status_var = "on"
                logger.debug(f"Log agent status: {log_status_var}")
                print(log_status_var) #### TO DO DEBUG: cambiar formato mensaje 
            else:
                logger.debug(f"Log agent status: {log_status_var}")
                log_status_var = "stand-by"
                logger.debug(f"Log agent status: {log_status_var}")
                        #### TO DO DEBUG: cambiar formato mensaje 

        async def on_end(self):
            active_agents.to_csv('ActiveAgents.csv', header = True, index = False)
            await self.agent.stop()

        async def on_start(self):
            self.counter = 1
            
    async def setup(self):
        b = self.LogBehav()
        template = Template()
        template.metadata = {"performative": "inform"}
        self.add_behaviour(b, template)
        fileh = logging.FileHandler(f'{my_dir}/{my_name}.log')
        formatter = logging.Formatter(f'%(asctime)s;%(levelname)s;{my_full_name};%(pathname)s;%(message)s')
        fileh.setFormatter(formatter)
        log = logging.getLogger()  # root logger
        for hdlr in log.handlers[:]:  # remove all old handlers
            log.removeHandler(hdlr)
        log.addHandler(fileh)
        if args.verbose == "DEBUG":
            logger.setLevel(logging.DEBUG)
        elif args.verbose == "INFO":
            logger.setLevel(logging.INFO)
        elif args.verbose == "WARNING":
            logger.setLevel(logging.WARNING)
        elif args.verbose == "ERROR":
            logger.setLevel(logging.ERROR)
        elif args.verbose == "CRITICAL":
            logger.setLevel(logging.CRITICAL)
        else:
            print('not valid verbosity')
        "IP"
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_machine = s.getsockname()[0]
        start_msg = asf.send_activation_finish(my_full_name, ip_machine, 'start')
        logger.debug(start_msg)


if __name__ == "__main__":
    """Parser parameters"""
    parser = argparse.ArgumentParser(description='Log parser')
    parser.add_argument('-an', '--agent_number', type=int, metavar='', required=False, default=1, help='agent_number: 1,2,3,4..')
    parser.add_argument('-v', '--verbose', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], metavar='', required=False, default='DEBUG', help='verbose: amount of information saved')
    parser.add_argument('-w', '--wait_msg_time', type=int, metavar='', required=False, default=120, help='wait_msg_time: time in seconds to wait for a msg. Purpose of system monitoring')
    parser.add_argument('-st', '--stop_time', type=int, metavar='', required=False, default=84600, help='stop_time: time in seconds where agent isnt asleep')
    parser.add_argument('-do', '--delete_order', type=str, metavar='', required=False, default='No', help='Order to delete') #29/04
    args = parser.parse_args()
    my_dir = os.getcwd()
    my_name = os.path.basename(__file__)[:-3]
    delete_order = args.delete_order
    my_full_name = opf.my_full_name(my_name, args.agent_number)
    wait_msg_time = args.wait_msg_time
    log_status_var = "Stand-by"


    """Logger info"""
    logger = logging.getLogger(__name__)

    """XMPP info"""
    log_jid = opf.agent_jid(my_dir, my_full_name)
    log_passwd = opf.agent_passwd(my_dir, my_full_name)
    log_agent = LogAgent(log_jid, log_passwd)
    future = log_agent.start(auto_register=True)
    future.result()

    """Counter"""
    stop_time = datetime.datetime.now() + datetime.timedelta(seconds=args.stop_time)
    while datetime.datetime.now() < stop_time:
        time.sleep(1)
    else:
        log_agent.stop()
        log_status_var = "off"
        logger.critical(f"{my_full_name}_agent stopped, coil_status_var: {log_status_var}")
        #### TO DO: cambiar formato mensaje 
        quit_spade()
        # while 1:
