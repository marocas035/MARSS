from spade import quit_spade
import time
import datetime
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from spade.template import Template
from spade.message import Message
import sys
import pandas as pd
import argparse
import operative_functions as opf
import os
import socket
import json
import aioxmpp
from aioxmpp import PresenceState, PresenceShow


class CoilAgent(Agent):
    class CoilBehav(PeriodicBehaviour):
        async def run(self):
            global my_full_name, my_dir, wait_msg_time, coil_status_var, coil_started_at, stop_time, refresh_time, coil_agent, coil_data_df, bid_register_df, ca_coil_msg_sender, not_entered_auctions, ip_machine, seq_coil #, auction_finish_at            
            """inform log of status"""
            coil_activation_json = opf.activation_df(my_full_name, coil_started_at)
            coil_msg_log = opf.msg_to_log(coil_activation_json, my_dir)
            await self.send(coil_msg_log)
            
            if (args.code != 'cO00000000'):
                coil_name = 'coil_00' + str(args.agent_number)
                activation_coil = opf.inform_coil_activation(my_full_name, args.code , coil_name , args.location).to_json(orient="records")
                activation_coil_msg = opf.activation_coil_inform_msg(activation_coil,  my_dir)
                await self.send(activation_coil_msg)
            
            "Ask browser to search order" 
            if (coil_search != "No")&(datetime.datetime.now() < searching_time):
                msg_to_search = 'Search:' + coil_search + ':' + my_full_name
                order_to_search_json = opf.search_br(my_full_name, msg_to_search).to_json(orient="records")
                coil_search_browser = opf.order_to_search(order_to_search_json, my_full_name, my_dir)
                await self.send(coil_search_browser)
                
            "Ask browser to delete order in register"
            if (coil_delete != "No")&(datetime.datetime.now() < searching_time):
                erase_order_msg= 'Delete order:' + coil_delete + ':' + my_full_name
                order_to_erase_json = opf.order_to_erase_json(my_full_name, erase_order_msg).to_json(orient="records")
                coil_delete_order = opf.order_to_erase(order_to_erase_json, my_full_name, my_dir)
                await self.send(coil_delete_order)
            
            "Ask browser for active agents in the system"
            if  (active_agents != "No")&(datetime.datetime.now() < searching_time):
                r = 'Request contact list'
                rq_contact_list = opf.rq_aa_br(my_full_name, r).to_json(orient="records")   #request contact list to browser
                rq_contact_list_json = opf.contact_list_br_json(rq_contact_list, my_dir)
                await self.send(rq_contact_list_json)
            
            "Ask browser for coil in the system df"
            if (coil_df != "No")&(datetime.datetime.now() < searching_time):
                r = 'Request contact list'
                rq_contact_list = opf.rq_cd_br(my_full_name, r).to_json(orient="records")  
                rq_contact_list_json = opf.contact_list_br_json(rq_contact_list, my_dir)
                await self.send(rq_contact_list_json)
                    
            if coil_status_var == "auction":
                """inform log of status"""
                to_do = "search-auction"
                coil_msg_log_body = opf.inform_log_df(my_full_name, coil_started_at, coil_status_var, to_do).to_json(orient="records")
                coil_msg_log = opf.msg_to_log(coil_msg_log_body, my_dir)
                await self.send(coil_msg_log)
                this_time = datetime.datetime.now()
                print(coil_status_var)
                # it will wait here for ca's that are auctionable.
                ca_coil_msg = await self.receive(timeout=wait_msg_time)
                if ca_coil_msg:
                    msg_sender_jid = str(va_coil_msg.sender)
                    msg_sender_jid = msg_sender_jid[:-33]
                    if msg_sender_jid == "browse":
                        br_msg_df = pd.read_json(msg.body)
                        if msg_df.loc[0, 'purpose'] =="search_requested":
                            order_searched = msg_df.loc[0, 'msg']  
                            print(order_searched)
                        elif msg_df.loc[0, 'purpose'] =="contact_list":
                            request = msg_df.loc[0, 'msg']   
                            print(request)
                    elif msg_sender_jid == "launch":
                        la_coil_msg_df = pd.read_json(ca_coil_msg.body)
                        coil_df.loc[0, 'budget'] = la_coil_msg_df.loc[0, 'budget']
                    elif (msg_sender_jid == "ca") or (msg_sender_jid == "va") :
                        seq_coil = seq_coil + 1
                        ca_coil_msg_df = pd.read_json(ca_coil_msg.body)
                        """Evaluate if resource conditions are acceptable to enter auction"""
                        # rating to difference of temperature between resource and coil parameters
                        coil_enter_auction_rating = opf.coil_enter_auction_rating(ca_coil_msg_df, coil_data_df, not_entered_auctions)
                        print(f'ca_coil_msg_df: {ca_coil_msg_df.to_string()}')
                        if coil_enter_auction_rating == 1:
                            #auction_level = ca_coil_msg_df.loc[0, 'auction_level']
                            """Create initial Bid"""
                            coil_bid = opf.coil_bid(ca_coil_msg_df, coil_data_df, coil_status_var)
                            """Send bid to ca"""
                            coil_ca_msg = opf.msg_to_sender(ca_coil_msg)
                            coil_data_df.loc[0, 'bid'] = coil_bid
                            coil_data_df.loc[0, 'bid_status'] = 'counterbid'
                            coil_ca_msg.body = coil_data_df.to_json()
                            await self.send(coil_ca_msg)
                          
                            """Store initial Bid"""
                            bid_level = 'initial'
                            bid_register_df = opf.append_bid(coil_bid, bid_register_df, my_name, my_full_name, ca_coil_msg_df, bid_level)
                            """inform log of status"""
                            coil_status_var = "auction"  # moves now to auction status
                            coil_inform_json = opf.inform_log_df(my_full_name, coil_started_at, coil_status_var).to_json()
                            coil_msg_log = opf.msg_to_log(coil_inform_json, my_dir)
                            await self.send(coil_msg_log)
                            """inform log of bid_register"""
                            coil_inform_json = bid_register_df.to_json()
                            coil_msg_log = opf.msg_to_log(coil_inform_json, my_dir)
                            await self.send(coil_msg_log)
                            """Receive request to counterbid or acceptedbid"""
                            ca_coil_msg2 = await self.receive(timeout=wait_msg_time)
                            # add counter to come back to stand-by if auction does not come to and end.
                            if ca_coil_msg2:
                                ca_coil_msg_df = pd.read_json(ca_coil_msg2.body)
                                if ca_coil_msg2.sender == ca_coil_msg_sender:  # checks if communication comes from last sender
                                    a = ca_coil_msg_df.at[0, 'bid_status']
                                    print(f'{a}')
                                    print(ca_coil_msg_df)
                                    if ca_coil_msg_df.at[0, 'bid_status'] == 'acceptedbid':
                                        """Store accepted Bid from ca agent"""
                                        bid_level = 'acceptedbid'
                                        bid_register_df = opf.append_bid(coil_bid, bid_register_df, my_name, my_full_name, ca_coil_msg_df, bid_level)
                                        """inform log of bid_register"""
                                        coil_inform_json = bid_register_df.to_json()
                                        coil_msg_log = opf.msg_to_log(coil_inform_json, my_dir)
                                        await self.send(coil_msg_log)
                                        """Confirm or deny assignation"""
                                        best_auction_agent_full_name = opf.compare_auctions(bid_register_df)
                                        """Store accepted Bid from coil agent"""
                                        bid_level = 'confirm'
                                        accepted_jid = opf.get_agent_jid(best_auction_agent_full_name)
                                        bid_register_df = opf.append_bid(coil_bid, bid_register_df, my_name, my_full_name, ca_coil_msg_df, bid_level, best_auction_agent_full_name)
                                        print(f'accepted jid: {accepted_jid}')
                                        print(f'ca_coil_msg_sender jid: {ca_coil_msg_sender}')
                                        ca_coil_msg_sender_f = str(ca_coil_msg_sender)[:-9]
                                        print(f'ca_coil_msg_sender jid: {ca_coil_msg_sender_f}')
                                        accepted_jid = str(accepted_jid)
                                        if accepted_jid == ca_coil_msg_sender_f:
                                            # confirm assignation. Else nothing
                                            coil_ca_msg = opf.msg_to_sender(ca_coil_msg)
                                            coil_data_df.loc[0, 'bid'] = coil_bid
                                            coil_data_df.loc[0, 'bid_status'] = 'acceptedbid'
                                            coil_ca_msg.body = coil_data_df.to_json()
                                            await self.send(coil_ca_msg)
                                            """inform log of auction won"""
                                            ca_id = ca_coil_msg_df.loc[0, 'id']
                                            this_time = datetime.datetime.now()
                                            coil_msg_log_body = f'{my_full_name} won auction to process in {ca_id} at {this_time}'
                                            coil_msg_log = opf.msg_to_log(coil_msg_log_body, my_dir)
                                            await self.send(coil_msg_log)
                                            print(coil_msg_log_body)
                                            """inform log status change"""
                                            coil_status_var = "sleep"  # changes to sleep
                                            coil_inform_json = opf.inform_log_df(my_full_name, coil_started_at, coil_status_var).to_json()
                                            coil_msg_log = opf.msg_to_log(coil_inform_json, my_dir)
                                            await self.send(coil_msg_log)
                                            """inform log of bid_register"""
                                            coil_inform_json = bid_register_df.to_json()
                                            coil_msg_log = opf.msg_to_log(coil_inform_json, my_dir)
                                            await self.send(coil_msg_log)
                                        else:
                                            """inform log of issue"""
                                            ca_id = ca_coil_msg_df.loc[0, 'id']
                                            coil_msg_log_body = f'{my_full_name} did not accept to process in {ca_id} in final acceptance'
                                            coil_msg_log = opf.msg_to_log(coil_msg_log_body, my_dir)
                                            await self.send(coil_msg_log)
                                            print(coil_msg_log_body)
                                    elif ca_coil_msg_df.at[0, 'bid_status'] == 'extrabid':
                                        """Create extra Bid"""
                                        coil_bid = opf.coil_bid(ca_coil_msg_df, coil_data_df, coil_status_var)  # will give 15% extra budget
                                        """Store extra Bid"""
                                        bid_level = 'extrabid'
                                        bid_register_df = opf.append_bid(coil_bid, bid_register_df, my_name, my_full_name, ca_coil_msg_df, bid_level)
                                        """Send bid to ca"""
                                        coil_ca_msg = opf.msg_to_sender(ca_coil_msg2)
                                        coil_data_df.loc[0, 'bid'] = coil_bid
                                        coil_data_df.loc[0, 'CounterBid'] = 'counterbid'
                                        coil_ca_msg.body = coil_data_df.to_json()
                                        await self.send(coil_ca_msg)
                                        ca_coil_msg_sender = ca_coil_msg2.sender
                                        """inform log of bid_register"""
                                        coil_inform_json = bid_register_df.to_json()
                                        coil_msg_log = opf.msg_to_log(coil_inform_json, my_dir)
                                        await self.send(coil_msg_log)
                                        """Wait to receive acceptance"""
                                        ca_coil_msg3 = await self.receive(timeout=wait_msg_time)
                                        # add counter to come back to stand-by if auction does not come to and end.
                                        if ca_coil_msg3:
                                            ca_coil_msg_df = pd.read_json(ca_coil_msg3.body)
                                            if ca_coil_msg3.sender == ca_coil_msg_sender:  # checks if communication comes from last sender
                                                a = ca_coil_msg_df.at[0, 'bid_status']
                                                print(f'{a}')
                                                print(ca_coil_msg_df)
                                                if ca_coil_msg_df.at[0, 'bid_status'] == 'acceptedbid' and ca_coil_msg_df.at[0, 'auction_level'] == 3:
                                                    """Store accepted Bid from ca agent"""
                                                    bid_level = 'acceptedbid'
                                                    bid_register_df = opf.append_bid(coil_bid, bid_register_df, my_name, my_full_name, ca_coil_msg_df, bid_level)
                                                    """inform log of bid_register"""
                                                    coil_inform_json = bid_register_df.to_json()
                                                    coil_msg_log = opf.msg_to_log(coil_inform_json, my_dir)
                                                    await self.send(coil_msg_log)
                                                    """Confirm or deny assignation"""
                                                    best_auction_agent_full_name = opf.compare_auctions(bid_register_df)
                                                    """Store accepted Bid from coil agent"""
                                                    bid_level = 'confirm'
                                                    accepted_jid = opf.get_agent_jid(best_auction_agent_full_name)
                                                    bid_register_df = opf.append_bid(coil_bid, bid_register_df, my_name, my_full_name, ca_coil_msg_df, bid_level, best_auction_agent_full_name)
                                                    print(f'accepted jid: {accepted_jid}')
                                                    print(f'ca_coil_msg_sender jid: {ca_coil_msg_sender}')
                                                    ca_coil_msg_sender_f = str(ca_coil_msg_sender)[:-9]
                                                    print(f'ca_coil_msg_sender jid: {ca_coil_msg_sender_f}')
                                                    accepted_jid = str(accepted_jid)
                                                    if accepted_jid == ca_coil_msg_sender_f:
                                                        # confirm assignation. Else nothing
                                                        coil_ca_msg = opf.msg_to_sender(ca_coil_msg)
                                                        coil_data_df.loc[0, 'bid'] = coil_bid
                                                        coil_data_df.loc[0, 'bid_status'] = 'acceptedbid'
                                                        coil_ca_msg.body = coil_data_df.to_json()
                                                        await self.send(coil_ca_msg)
                                                        """inform log of auction won"""
                                                        ca_id = ca_coil_msg_df.loc[0, 'id']
                                                        this_time = datetime.datetime.now()
                                                        coil_msg_log_body = f'{my_full_name} won auction to process in {ca_id} at {this_time}'
                                                        coil_msg_log = opf.msg_to_log(coil_msg_log_body, my_dir)
                                                        await self.send(coil_msg_log)
                                                        print(coil_msg_log_body)
                                                        """inform log status change"""
                                                        coil_status_var = "sleep"  # changes to sleep
                                                        coil_inform_json = opf.inform_log_df(my_full_name, coil_started_at, coil_status_var).to_json()
                                                        coil_msg_log = opf.msg_to_log(coil_inform_json, my_dir)
                                                        await self.send(coil_msg_log)
                                                        """inform log of bid_register"""
                                                        coil_inform_json = bid_register_df.to_json()
                                                        coil_msg_log = opf.msg_to_log(coil_inform_json, my_dir)
                                                        await self.send(coil_msg_log)
                                                    else:
                                                        """inform log of issue"""
                                                        ca_id = ca_coil_msg_df.loc[0, 'id']
                                                        coil_msg_log_body = f'{my_full_name} did not accept to process in {ca_id} in final acceptance'
                                                        coil_msg_log_body = opf.inform_error(coil_msg_log_body)
                                                        coil_msg_log = opf.msg_to_log(coil_msg_log_body, my_dir)
                                                        await self.send(coil_msg_log)
                                                else:
                                                    """inform log of issue"""
                                                    ca_id = ca_coil_msg_df.loc[0, 'id']
                                                    ca_bid_status = ca_coil_msg_df.at[0, 'bid_status']
                                                    ca_auction_level = ca_coil_msg_df.at[0, 'auction_level']
                                                    coil_msg_log_body = f'{my_full_name} received wrong message from {ca_id} in final acceptance. ca_auction_level: {ca_auction_level}!= 3 or ca_bid_status: {ca_bid_status} != accepted'                                                    
                                                    coil_msg_log_body = opf.inform_error(coil_msg_log_body)
                                                    coil_msg_log = opf.msg_to_log(coil_msg_log_body, my_dir)
                                                    await self.send(coil_msg_log)
                                            else:
                                                """inform log of issue"""
                                                coil_msg_log_body = f'incorrect sender'
                                                coil_msg_log_body = opf.inform_error(coil_msg_log_body)
                                                coil_msg_log = opf.msg_to_log(coil_msg_log_body, my_dir)
                                                await self.send(coil_msg_log)
                                                
                                        else:
                                            """inform log"""
                                            coil_msg_log_body = f'{my_full_name} did not receive any msg in the last {wait_msg_time}s at {coil_status_var} at last auction level'
                                            coil_msg_log = opf.msg_to_log(coil_msg_log_body, my_dir)
                                            await self.send(coil_msg_log)
                                        print(coil_msg_log_body)
                                else:
                                    """inform log of issue"""
                                    coil_msg_log_body = f'incorrect sender'
                                    coil_msg_log_body = opf.inform_error(coil_msg_log_body)
                                    coil_msg_log = opf.msg_to_log(coil_msg_log_body, my_dir)
                                    await self.send(coil_msg_log)
                            else:
                                """inform log"""
                                coil_msg_log_body = f'{my_full_name} did not receive any msg in the last {wait_msg_time}s at {coil_status_var} at last auction level'
                                coil_msg_log_body = opf.inform_error(coil_msg_log_body)
                                coil_msg_log = opf.msg_to_log(coil_msg_log_body, my_dir)
                                await self.send(coil_msg_log)
                        else:
                            """inform log of status"""
                            to_do = "search-auction"
                            ca_id = ca_coil_msg_df.loc[0, 'id']
                            not_entered_auctions += int(1)
                            entered_auction_str = f'{my_full_name} did not enter {ca_id} auction because Temp difference was too high. Not_entered auction number: {not_entered_auctions}'
                            coil_msg_log_body = opf.inform_error(entered_auction_str)
                            coil_msg_log = opf.msg_to_log(coil_msg_log_body, my_dir)
                            await self.send(coil_msg_log)
                else:
                    """inform log"""
                    coil_msg_log_body = f'{my_full_name} did not receive any msg in the last {wait_msg_time}s at {coil_status_var}'
                    coil_msg_log_body = opf.inform_error(coil_msg_log_body)
                    coil_msg_log = opf.msg_to_log(coil_msg_log_body, my_dir)
                    await self.send(coil_msg_log)
                    
            elif coil_status_var == "sleep":
                """wait for message from in case fabrication was interrupted"""
                interrupted_fab_msg = await self.receive(timeout=wait_msg_time)
                if interrupted_fab_msg:
                    interrupted_fab_msg_sender = interrupted_fab_msg.sender
                    if interrupted_fab_msg_sender[:-33] == "bro":
                        interrupted_fab_msg_df = pd.read_json(interrupted_fab_msg)
                        if interrupted_fab_msg_df.loc[0, 'int_fab'] == 1:
                            coil_data_df.loc[0, 'int_fab'] = 1
                            coil_status_var = "stand-by"
                            """inform log of issue"""
                            this_time = datetime.datetime.now()
                            coil_msg_log_body = f'{my_full_name} interrupted fab. Received that msg at {this_time}'
                            coil_msg_log = opf.msg_to_log(coil_msg_log_body, my_dir)
                            await self.send(coil_msg_log)
                            print(coil_msg_log_body)
                    else:
                        """inform log"""
                        time.sleep(5)
                        coil_msg_log_body = f'{my_full_name} receive msg at {coil_status_var}, but not from browser'
                        coil_msg_log_body = opf.inform_error(coil_msg_log_body)
                        coil_msg_log = opf.msg_to_log(coil_msg_log_body, my_dir)
                        await self.send(coil_msg_log)
                else:
                    """inform log"""
                    time.sleep(10)
                    coil_msg_log_body = f'{my_full_name} did not receive any msg in the last {wait_msg_time}s at {coil_status_var}'
                    coil_msg_log_body = opf.inform_error(coil_msg_log_body)
                    coil_msg_log = opf.msg_to_log(coil_msg_log_body, my_dir)
                    await self.send(coil_msg_log)
                    now_time = datetime.datetime.now()
                    tiempo = now_time - auction_finish_at
                    segundos = tiempo.seconds
                    if segundos > 50:
                        opf.change_jid(my_dir, my_full_name)
                        self.kill()
                    
                    
            elif coil_status_var == "stand-by":  # stand-by status for BR is not very useful, just in case we need the agent to be alive, but not operative. At the moment, it won      t change to stand-by.
                """inform log of status"""
                coil_inform_json = opf.inform_log_df(my_full_name, coil_started_at, coil_status_var).to_json()
                coil_msg_log = opf.msg_to_log(coil_inform_json, my_dir)
                await self.send(coil_msg_log)
               # now it just changes directly to auction
                coil_status_var = "auction"
            else:
                """inform log of status"""
                coil_inform_json = opf.inform_log_df(my_full_name, coil_started_at, coil_status_var).to_json()
                coil_msg_log = opf.msg_to_log(coil_inform_json, my_dir)
                await self.send(coil_msg_log)
                coil_status_var = "stand-by"
                
        async def on_end(self):
            """Inform log """
            coil_msg_end = opf.send_activation_finish(my_full_name, ip_machine, 'end')
            va_msg_log = opf.msg_to_log(coil_msg_end, my_dir)
            await self.send(va_msg_log)
            await self.agent.stop()
            
            def unsuscribe(self):
                """Asks for unsubscription"""
                self.roster.unsubscribe(aioxmpp.JID.fromstr(log@apiict03.etsii.upm.es).bare())

        async def on_start(self):
            self.counter = 1
            """inform log of start"""
            coil_msg_start = opf.send_activation_finish(my_full_name, ip_machine, 'start')
            coil_msg_start = opf.msg_to_log(coil_msg_start, my_dir)
            await self.send(coil_msg_start)
            
            def suscribe(self):
                """Asks for subscription"""
                self.roster.subscribe(aioxmpp.JID.fromstr(log@apiict03.etsii.upm.es).bare())

    async def setup(self):
        start_at = datetime.datetime.now() + datetime.timedelta(seconds=3)
        b = self.CoilBehav(period=3, start_at=start_at)  # periodic sender
        template = Template()
        template.metadata = {"performative": "inform"}
        self.add_behaviour(b)


if __name__ == "__main__":
    """Parser parameters"""
    parser = argparse.ArgumentParser(description='coil parser')
    parser.add_argument('-an', '--agent_number', type=int, metavar='', required=False, default=1, help='agent_number: 1,2,3,4..')
    parser.add_argument('-v', '--wait_msg_time', type=int, metavar='', required=False, default=20, help='wait_msg_time: time in seconds to wait for a msg. Purpose of system monitoring')
    parser.add_argument('-st', '--stop_time', type=int, metavar='', required=False, default=84600, help='stop_time: time in seconds where agent isnt asleep')
    parser.add_argument('-s', '--status', type=str, metavar='', required=False, default='stand-by', help='status_var: on, stand-by, off')
    parser.add_argument('-b', '--budget', type=int, metavar='', required=False, default=100, help='budget: in case of needed, budget can be increased')
    parser.add_argument('--search', type=str, metavar='', required=False, default='No',help='Search order by code. Write depending on your case: aa=list (list active agents), oc(order_code), sg(steel_grade),at(average_thickness), wi(width_coils), ic(id_coil), so(string_operations), date. Example: --search oc=cO202106101')
    parser.add_argument('-set', '--search_time', type=int, metavar='', required=False, default=1, help='search_time: time in seconds where agent is searching by code')
    parser.add_argument('-do', '--delete', type=str, metavar='', required=False, default='No', help='Delete order in register given a code to filter')
    parser.add_argument('-l', '--location', type=str, metavar='', required=False, default='K', help='location: K')
    parser.add_argument('-c', '--code', type=str, metavar='', required=False, default='cO00000000',help='code: cO202106101')
    parser.add_argument('-w', '--wait_auction_time', type=int, metavar='', required=False, default=500, help='wait_msg_time: time in seconds to wait for a msg')
    parser.add_argument('-aa', '--active_agents', type=str, metavar='', required=False, default='No', help='Write Y to Ask for list of active agents in the system')
    parser.add_argument('-cd', '--coil_df', type=str, metavar='', required=False, default='No', help='Write Y to Ask for list of active coils and their localitation')
    args = parser.parse_args()
    my_dir = os.getcwd()
    my_name = os.path.basename(__file__)[:-3]
    my_full_name = opf.my_full_name(my_name, args.agent_number)
    wait_msg_time = args.wait_msg_time
    auction_time = args.wait_auction_time
    coil_started_at = datetime.datetime.now().time()
    coil_status_var = args.status
    coil_search = args.search
    coil_delete = args.delete
    active_agents = args.active_agents
    coil_df = args.coil_df
    refresh_time = datetime.datetime.now() + datetime.timedelta(seconds=1)
    searching_time = datetime.datetime.now() + datetime.timedelta(seconds=args.search_time)
    
    """Save to csv who I am"""
    opf.set_agent_parameters(my_dir, my_name, my_full_name)
    coil_data_df = pd.read_csv(f'{my_full_name}.csv', header=0, delimiter=",", engine='python')
    coil_data_df.at[0, 'budget'] = args.budget
    budget = coil_data_df.loc[0, 'budget']
    bid_register_df = opf.bid_register(my_name, my_full_name)
    not_entered_auctions = int(0)
    seq_coil = int(200)
    
    "IP"
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip_machine = s.getsockname()[0]
    
    """XMPP info"""
    coil_jid = opf.agent_jid(my_dir, my_full_name)
    coil_passwd = opf.agent_passwd(my_dir, my_full_name)
    coil_agent = CoilAgent(coil_jid, coil_passwd)
    future = coil_agent.start(auto_register=True)
    future.result()
    
    """Counter"""
    stop_time = datetime.datetime.now() + datetime.timedelta(seconds=args.stop_time)
    while datetime.datetime.now() < stop_time:
        time.sleep(1)
    else:
        coil_status_var = "off"
        coil_agent.stop()
        quit_spade()

# agent will live as set as stop_time and inform to log when it stops at status_var == "stand-by"
