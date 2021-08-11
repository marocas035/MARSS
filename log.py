from spade import quit_spade
import time
import datetime
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
import json
import socket
import aioxmpp
from aioxmpp import PresenceState, PresenceShow


class LogAgent(Agent):
    class LogBehav(CyclicBehaviour):            
        async def run(self):
            self.presence.on_subscribe = self.on_subscribe
            self.presence.on_subscribed = self.on_subscribed
            global wait_msg_time, logger, log_status_var, active_agents, ip_machine, list_contacts
            if log_status_var == "on":
                '''"Active Agents"   #todo
                r = opf.checkFileExistance()
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
                                my_list1 = {'agent_id': msg2_sender_jid2, 'agent_name': m[2], 'agent_type': typeaa,
                                            'activation_time': m[4]}
                                active_agents = active_agents.append(my_list1, ignore_index=True)
                                active_agents = active_agents.drop_duplicates(['agent_id', 'agent_name'], keep='first')
                        remove('ActiveAgents.csv')
                        del a'''
                msg = await self.receive(timeout=wait_msg_time)  # wait for a message for 20 seconds
                if msg:
                    print(f"received msg number {self.counter}")
                    self.counter += 1
                    counter = int(self.counter)
                    #logger.info(msg.body)
                    msg_sender_jid0 = str(msg.sender)
                    msg_sender_jid = msg_sender_jid0[:-31]
                    msg_sender_jid2 = msg_sender_jid0[:-9]
                    agent_type = opf.aa_type(msg_sender_jid2)
                    self.presence.subscribe(msg_sender_jid0)
                    #approve(msg_sender_jid0)
                    list_contacts = opf.get_contacts(self)
                    print(list_contacts)
                    '''time = datetime.datetime.now()
                    """Active agents register"""
                    my_list = [{'agent_id': msg_sender_jid2, 'agent_name': msg_sender_jid, 'agent_type': agent_type,
                                'activation_time': time}]
                    if (counter == 2):
                        active_agents = pd.DataFrame([], columns=['agent_id', 'agent_name', 'agent_type',
                                                                  'activation_time'])
                        active_agents = active_agents.append(my_list, ignore_index=True)
                    else:
                        active_agents = active_agents.append(my_list, ignore_index=True)
                        active_agents = active_agents.drop_duplicates(['agent_id', 'agent_name'], keep='first')
                    # print(active_agents)
                    agent_register = f'ActiveAgent: agent_id:{msg_sender_jid2}, agent_name:{msg_sender_jid}, type:{agent_type}, active_time:{datetime.datetime.now()}'
                    agent_register = opf.inform_register_aa(agent_register)
                    logger.info(agent_register)'''
                    """Log file"""
                    fileh = logging.FileHandler(f'{my_dir}/{my_name}.log')
                    formatter = logging.Formatter(f'%(asctime)s;%(levelname)s;{agent_type};%(pathname)s;%(message)s')
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
                    elif 'IP' in msg_2:  # msg_2.loc[0, 'purpose'] == 'inform' or ###jose???
                        logger.debug(msg.body)
                    elif 'active_coils' in msg_2:
                        logger.critical(msg.body)
                    else:
                        logger.info(msg.body)
                    """Update coil status """
                    x = re.search("won auction to process", msg.body)
                    if x:  # update  coil status
                        auction = msg.body.split(" ")
                        coil_id = auction[0]
                        status = auction[6]
                        o = opf.checkFile2Existance()
                        if o == True:
                            opf.update_coil_status(coil_id, status)
                            updated_coil = f'Coil: {coil_id} updated status'
                            updated_coil = opf.update_coil_status(updated_coil)
                            logger.info(updated_coil)
                    elif msg_sender_jid == "launcher":
                        launcher_df = pd.read_json(msg.body)
                        if 'order_code' in launcher_df:   # Save order
                            opf.save_order(msg.body)
                            logger.info(msg.body)
                            ack_msg = "new order successfully saved"
                            log_msg_la = opf.msg_to_launcher(ack_msg, my_dir)
                            await self.send(log_msg_la)
                    elif msg_sender_jid == "browser":
                        browser_df = pd.read_json(msg.body)
                        if 'SearchAA' in browser_df:  # Active agents list requested   #####¿¿¿¿?¿?¿?¿? #todo
                            logger.info(msg.body)
                            list_aa = str(active_agents)
                            log_msg_br = opf.msg_aa_to_br(list_aa, my_dir)
                            await self.send(log_msg_br)
                else:
                    msg = f"Log_agent didn't receive any msg in the last {wait_msg_time}s"
                    msg = opf.inform_error(msg)
                    logger.debug(msg)
            elif log_status_var == "stand-by":
                status_log = opf.log_status(my_full_name, log_status_var, ip_machine)
                logger.debug(status_log)

                log_status_var = "on"
                status_log = opf.log_status(my_full_name, log_status_var, ip_machine)
                logger.debug(status_log)
            else:
                status_log = opf.log_status(my_full_name, log_status_var, ip_machine)
                logger.debug(status_log)
                log_status_var = "stand-by"
                status_log = opf.log_status(my_full_name, log_status_var, ip_machine)
                logger.debug(status_log)


        async def on_end(self):
            #active_agents.to_csv('ActiveAgents.csv', header=True, index=False)   ####### CAMBIAR -CONTACT LIST? #todo
            await self.agent.stop()

        async def on_start(self):
            self.counter = 1
            list_contacts = {}
            self._contacts = {}
            
        async def on_subscribe(self, jid):
            print("[{}] Agent {} asked for subscription. Let's aprove it.".format(self.agent.name, jid.split("@")[0]))
            self.presence.approve(jid)
            self.presence.subscribe(jid)
            
        async def on_subscribed(self, jid):
            print("[{}] Agent {} has accepted the subscription.".format(self.agent.name, jid.split("@")[0]))
            print("[{}] Contacts List: {}".format(self.agent.name, self.agent.presence.get_contacts()))
            
        '''async def get_contacts(self):
            """Returns list of contacts"""
            for jid, item in self.roster.items.items():
                try:
                    self._contacts[jid.bare()].update(item.export_as_json())
                except KeyError:
                    self._contacts[jid.bare()] = item.export_as_json()

        return self._contacts'''   

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
        start_msg = opf.send_activation_finish(my_full_name, ip_machine, 'start') #### TO DO FUNCION
        logger.debug(start_msg)


if __name__ == "__main__":
    """Parser parameters"""
    parser = argparse.ArgumentParser(description='Log parser')
    parser.add_argument('-an', '--agent_number', type=int, metavar='', required=False, default=1,
                        help='agent_number: 1,2,3,4..')
    parser.add_argument('-v', '--verbose', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        metavar='', required=False, default='DEBUG', help='verbose: amount of information saved')
    parser.add_argument('-w', '--wait_msg_time', type=int, metavar='', required=False, default=800,
                        help='wait_msg_time: time in seconds to wait for a msg. Purpose of system monitoring')
    parser.add_argument('-st', '--stop_time', type=int, metavar='', required=False, default=84600,
                        help='stop_time: time in seconds where agent isnt asleep')
    parser.add_argument('-do', '--delete_order', type=str, metavar='', required=False, default='No',
                        help='Order to delete')  # 29/04
    args = parser.parse_args()
    my_dir = os.getcwd()
    my_name = os.path.basename(__file__)[:-3]
    delete_order = args.delete_order
    my_full_name = opf.my_full_name(my_name, args.agent_number)
    wait_msg_time = args.wait_msg_time
    log_status_var = "stand-by"

    "IP"
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_machine = s.getsockname()[0]

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
        stop_msg_log = f"{my_full_name}_agent stopped, coil_status_var: {log_status_var}"
        stop_msg_log = json.dumps(stop_msg_log)
        logger.critical(stop_msg_log)
        quit_spade()
        # while 1:
