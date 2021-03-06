from spade import quit_spade
import argparse
import operative_functions as opf
import pandas as pd
import os
import time
import datetime
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour
from spade.template import Template
import json
import socket

class LaunchAgent(Agent):
    class LABehav(OneShotBehaviour):
        async def run(self):
            global la_status_var, my_full_name, la_started_at, stop_time, my_dir, wait_msg_time, ip_machine, counter,df
            
            """inform log of status"""
            la_activation_json = opf.activation_df(my_full_name, la_started_at)
            la_msg_log = opf.msg_to_log(la_activation_json, my_dir)
            await self.send(la_msg_log)
            
            """Send new order to log"""
            if order_code != "No":
                la_inform_log = opf.order_file(my_full_name, order_code, steel_grade, thickness, width_coils,
                                                    num_coils, list_coils, each_coil_price, list_ware, string_operations, wait_msg_time)
                la_inform_log_json = la_inform_log.to_json(orient="records")
                print(la_inform_log_json)
                la_order_log = opf.order_to_log(la_inform_log_json, my_dir)
                await self.send(la_order_log)
                
                """Active coil agents"""
                r = 'Request contact list'
                rq_contact_list = opf.rq_list_br(my_full_name, r).to_json(orient="records")   #request contact list to browser
                rq_contact_list_json = opf.contact_list_br_json(rq_contact_list, my_dir)
                await self.send(rq_contact_list_json)
                msg_cl = await self.receive(timeout=wait_msg_time) # wait for a message for 5 seconds
                if msg_cl:
                    
                    print('order succesfully saved')
                    
                    agent_df = pd.read_json(msg_cl.body)
                    list_id_coil_agent = ""
                    counter = 1
                    if agent_df.loc[0, 'purpose'] == "contact_list":
                        if (len(agent_df.columns)) == 5:
                            counter += 1
                            contact_list = agent_df.loc[0, 'msg1']
                            active_coil_df = agent_df.loc[0, 'msg2']
                        else:
                            contact_list = agent_df.loc[0, 'msg'] 
                        contact_jid = contact_list.split("JID(localpart='")
                        for i in contact_jid:
                            id_agent_list = i.split("', domain='apiict03.etsii.upm.es', resource=None): {'subscription': 'none', 'ask': 'subscribe'}")
                            id_agent = id_agent_list[0][0]
                            if id_agent == 'c':
                                id_coil_agent = id_agent_list[0][0:4]
                                list_id_coil_agent = list_id_coil_agent + id_coil_agent + ','        
                        list_id_coil_agents = f"{list_id_coil_agent}"
                        if (len(agent_df.columns)) == 5:
                            inform_log = opf.change_warehouse(la_inform_log, my_dir ,contact_list, counter,  active_coil_df)
                        else:
                            inform_log = opf.change_warehouse(la_inform_log, my_dir , contact_list, counter )
                            
            """Change in order"""                
            if name_coil != "No":
                la_coil_json = opf.order_budget(change_budget, name_coil).to_json(orient="records")
                msg_budget = opf.order_coil(la_coil_json, name_coil)
                await self.send(msg_budget)
                la_order_log = opf.order_to_log(la_coil_json, my_dir)
                await self.send(la_order_log)           
                
            """Send searching code to browser"""
            if la_search != "No":
                msg_to_search = 'Search:' + la_search + ':' + my_full_name
                order_to_search_json = opf.search_br(my_full_name, msg_to_search).to_json(orient="records")
                la_search_browser = opf.order_to_search(order_to_search_json, my_full_name, my_dir)
                await self.send(la_search_browser)

    class ReceiverBehav(OneShotBehaviour):
        async def run(self):
            await self.agent.b.join()
            """Receive message"""
            msg = await self.receive(timeout=wait_msg_time) # wait for a message for 5 seconds
            if msg:
                msg_df = pd.read_json(msg.body)
                if msg_df.loc[0, 'purpose'] =="search_requested":
                    order_searched = msg_df.loc[0, 'msg']  
                    print(order_searched)
    
                
        async def on_end(self):
            """Inform log """
            la_msg_ended = opf.send_activation_finish(my_full_name, ip_machine, 'end')
            la_msg_ended = opf.msg_to_log(la_msg_ended, my_dir)
            await self.send(la_msg_ended)
            await self.agent.stop()

        async def on_start(self):
            self.counter = 1

    async def setup(self):
        self.b = self.LABehav()
        template = Template()
        template.metadata = {"performative": "inform"}
        self.add_behaviour(self.b, template)
        self.b2 = self.ReceiverBehav()
        template2 = Template()
        template2.metadata = {"performative": "inform"}
        self.add_behaviour(self.b2, template2)


if __name__ == "__main__":
    """Parser parameters"""
    parser = argparse.ArgumentParser(description='wh parser')
    parser.add_argument('-an', '--agent_number', type=int, metavar='', required=False, default=1, help='agent_number: 1,2,3,4..')
    parser.add_argument('-w', '--wait_msg_time', type=int, metavar='', required=False, default=500, help='wait_msg_time: time in seconds to wait for a msg')
    parser.add_argument('-st', '--stop_time', type=int, metavar='', required=False, default=10, help='stop_time: time in seconds where agent')
    parser.add_argument('-s', '--status', type=str, metavar='', required=False, default='stand-by', help='status_var: on, stand-by, Off')
    parser.add_argument('--search', type=str, metavar='', required=False, default='No',help='Search order by code. Writte depending on your case: aa=list (list active agents), oc (order_code),sg(steel_grade),at(average_thickness), wi(width_coils), ic(id_coil), so(string_operations), date.Example: --search oc = 987')
    #DATOS DE PEDIDO:
    parser.add_argument('-oc', '--order_code', type=str, metavar='',required=False, default='No', help='Specify the number code of the order. Write between "x"')
    parser.add_argument('-sg', '--steel_grade', type=str, metavar='', required=False, default='1', help='Number which specifies the type of steel used for coils in an order.Write between "x"')
    parser.add_argument('-at', '--average_thickness', type=float, metavar='', required=False, default='0.4',help='Specify the thickness for coils ordered')
    parser.add_argument('-wi', '--width_coils', type=int, metavar='', required=False, default='950', help='Specify the width for coils ordered')
    parser.add_argument('-nc', '--number_coils', type=int, metavar='', required=False, default='1', help='Number of coils involved in the order')
    parser.add_argument('-lc', '--list_coils', type=str, metavar='', required=False, default='No', help='List of codes of coils involved in the order.Write between "x"')
    parser.add_argument('-po', '--price_order', type=float, metavar='', required=False, default='1', help='Price given to the order')
    parser.add_argument('-so', '--string_operations', type=str, metavar='', required=False, default='No', help='Sequence of operations needed.Write between "x".Format:"BZA|TD[2]|ENT[2|3]|HO[1|2]|NWW[1|4]|VA*[9|10|11]"')    
    parser.add_argument('-lp', '--list_position', type=str, metavar='', required=False, default='No',help='Coil warehouses.Write between ",".Format:K,L,K')
    parser.add_argument('-cb', '--change_budget', type=str, metavar='', required=False, default='210',
                        help='Specify the new budget. Write between "x"')
    parser.add_argument('-na', '--name_new_budget', type=str, metavar='', required=False, default='No',
                        help='Specify the coil of new budget. "cO202106101"')
    args = parser.parse_args()
    my_dir = os.getcwd()
    my_name = os.path.basename(__file__)[:-3]
    my_full_name = opf.my_full_name(my_name, args.agent_number)
    wait_msg_time = args.wait_msg_time
    la_started_at = datetime.datetime.now().time()
    la_status_var = args.status
    la_search = args.search
    order_code = args.order_code
    steel_grade = args.steel_grade
    thickness = args.average_thickness
    width_coils = args.width_coils
    num_coils = args.number_coils
    each_coil_price = round((args.price_order/args.number_coils),2)
    list_coils = args.list_coils
    string_operations = args.string_operations
    list_ware = args.list_position
    change_budget = args.change_budget
    name_coil = args.name_new_budget

    
    """Save to csv who I am"""
    la_data_df = opf.set_agent_parameters(my_dir, my_name, my_full_name)
    
    """IP"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_machine = s.getsockname()[0]
    
    """XMPP info"""
    la_jid = opf.agent_jid(my_dir, my_full_name)
    la_passwd = opf.agent_passwd(my_dir, my_full_name)
    la_agent = LaunchAgent(la_jid, la_passwd)
    future = la_agent.start(auto_register=True)
    future.result()
    la_agent.b2.join()
    
    """Counter"""
    stop_time = datetime.datetime.now() + datetime.timedelta(seconds=args.stop_time)
    while la_agent.is_alive():
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            la_status_var = "off"
            la_agent.stop()
    quit_spade()                   
                        
                        
