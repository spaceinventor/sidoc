# rft_procedure.py

import pycsh
import requests

class Procedure:
    def __init__(self, logger, args):
        self.logger = logger
        self.args = args


    def run(self):
        raise NotImplementedError("Subclasses should implement this method.")

    def send_google_chat_notification(self, message):
        """
        Sends a notification via Google Chat.
        """
        webhook_url = self.args.google_chat_webhook
        payload = {"text": message}
        headers = {"Content-Type": "application/json; charset=UTF-8"}

        try:
            response = requests.post(webhook_url, json=payload, headers=headers)
            if response.status_code == 200:
                self.logger.info("Notification sent successfully.")
            else:
                self.logger.warning(f"Failed to send notification: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")

    def check_power_supply(self):
        """
        Checks the power supply by reading voltage and current.
        """
        self.logger.info("Checking the power supply...")
        try:
            voltage = pycsh.get("psu_voltage_out", node=self.args.psu_node)
            current = pycsh.get("psu_current_out", node=self.args.psu_node)
            self.logger.info(f"Voltage: {voltage:.6f} V")
            self.logger.info(f"Current: {current:.6f} A")
        except Exception as e:
            self.logger.error(f"Error reading power supply parameters: {e}")
            voltage = 0
            current = 0

        power_consumption = voltage * current
        self.logger.info(f"Power Consumption: {power_consumption:.6f} W")
        return power_consumption


    def check_can_interface(self, interface_name: str, node: int):
        """
        Checks the statistics of a specified CAN interface on a given node.
        Returns the stats object if all checks pass, or None if there's a failure.
        """
        try:
            stats = pycsh.Ifstat(interface_name, node=node)

            # Log statistics
            self.logger.info(f"{interface_name} Interface Statistics on Node {node}:")
            self.logger.info(f"TX: {stats.tx}, RX: {stats.rx}")
            self.logger.info(f"TX Errors: {stats.tx_error}, RX Errors: {stats.rx_error}")
            self.logger.info(f"Dropped Packets: {stats.drop}, Auth Errors: {stats.autherr}")
            self.logger.info(f"TX Bytes: {stats.txbytes}, RX Bytes: {stats.rxbytes}")

            self.send_google_chat_notification(f"{interface_name} Interface Statistics on Node {node}:")
            self.send_google_chat_notification(f"TX: {stats.tx}, RX: {stats.rx}") 
            self.send_google_chat_notification(f"TX Errors: {stats.tx_error}, RX Errors: {stats.rx_error}") 
            self.send_google_chat_notification(f"Dropped Packets: {stats.drop}, Auth Errors: {stats.autherr}")
            self.send_google_chat_notification(f"TX Bytes: {stats.txbytes}, RX Bytes: {stats.rxbytes}")


            # Guard clause: if no packets have been transmitted or dropped
            total_packets = stats.tx + stats.drop
            if total_packets == 0:
                self.logger.warning(f"No packets transmitted on {interface_name} on Node {node} yet.")
                self.send_google_chat_notification(f"No packets transmitted on {interface_name} on Node {node} yet.")
                return None

            # Check if drop percentage exceeds 20%
            drop_percentage = (stats.drop / total_packets) * 100
            if drop_percentage >= 20:
                self.logger.warning(f"{drop_percentage:.2f}% of packets dropped on {interface_name} on Node {node}.")
                self.send_google_chat_notification(f"{drop_percentage:.2f}% of packets dropped on {interface_name} on Node {node}.")
                return stats

            # Check for transmission/reception errors
            if stats.tx_error > 0 or stats.rx_error > 0:
                self.logger.warning(f"Transmission/Reception errors on {interface_name} on Node {node}.")
                self.send_google_chat_notification(f"Transmission/Reception errors on {interface_name} on Node {node}.")
                return None
            if stats.autherr > 0:
                self.logger.warning(f"Authentication errors on {interface_name} on Node {node}.")
                self.send_google_chat_notification(f"Authentication errors on {interface_name} on Node {node}.")
                return None

            
            self.logger.info(f"{interface_name} appears to be operating correctly on Node {node}.")
            self.send_google_chat_notification(f"{interface_name} appears to be operating correctly on Node {node}.")

            return stats

        except Exception as e:
            self.logger.error(f"An error occurred while checking {interface_name} on Node {node}: {e}")
            self.send_google_chat_notification(f"An error occurred while checking {interface_name} on Node {node}: {e}")
            return None



    def can_checker(self):
        """
        Runs CAN interface checks for the specified interfaces on specified nodes.
        Always does a CAN0 vs CAN1 cross-compare, even if one interface fails.
        """
        self.logger.info("Starting CAN interface checks...")
        self.send_google_chat_notification("Starting CAN interface checks...")
        all_ok = True

        nodes = [self.args.can_node]
        interfaces = self.args.interfaces
        stats_map = {}  

        for node in nodes:
            self.logger.info(f"Checking interfaces on Node {node}...")
            node_stats = {}
            for interface in interfaces:
                stats_obj = self.check_can_interface(interface, node)
                if stats_obj is None:
                    all_ok = False
                    node_stats[interface] = None  # We store None so we know it failed
                else:
                    node_stats[interface] = stats_obj
            stats_map[node] = node_stats

        for node, ifstats in stats_map.items():
            if "CAN0" in ifstats and "CAN1" in ifstats:
                can0_stats = ifstats["CAN0"]
                can1_stats = ifstats["CAN1"]

                # If one is None, we force 0 for TX/RX to get a difference
                if can0_stats is None:
                    can0_rx = 0
                    can0_tx = 0
                    self.logger.warning(f"Node {node} - CAN0 stats are None (failed earlier). Using 0 for cross-compare.")
                    self.send_google_chat_notification(f"Node {node} - CAN0 stats are None (failed earlier). Using 0 for cross-compare.")
                else:
                    can0_rx = can0_stats.rx
                    can0_tx = can0_stats.tx

                if can1_stats is None:
                    can1_rx = 0
                    can1_tx = 0
                    self.logger.warning(f"Node {node} - CAN1 stats are None (failed earlier). Using 0 for cross-compare.")
                    self.send_google_chat_notification(f"Node {node} - CAN1 stats are None (failed earlier). Using 0 for cross-compare.")
                else:
                    can1_rx = can1_stats.rx
                    can1_tx = can1_stats.tx

                rx_diff = abs(can0_rx - can1_rx)
                tx_diff = abs(can0_tx - can1_tx)
                self.logger.info(
                    f"Cross-Compare Node {node}: CAN0.RX={can0_rx}, CAN1.RX={can1_rx}, "
                    f"CAN0.TX={can0_tx}, CAN1.TX={can1_tx}"
                )
                self.logger.info(f"RX diff = {rx_diff}, TX diff = {tx_diff}")
                self.send_google_chat_notification(
                    f"Cross-Compare Node {node}: CAN0.RX={can0_rx}, CAN1.RX={can1_rx}, "
                    f"CAN0.TX={can0_tx}, CAN1.TX={can1_tx}"
                )
                self.send_google_chat_notification(f"RX diff = {rx_diff}, TX diff = {tx_diff}")
            else:
                self.logger.info(f"Node {node} has no CAN0 vs CAN1 cross-comparison because both are not in 'interfaces'")
                self.send_google_chat_notification(f"Node {node} has no CAN0 vs CAN1 cross-comparison because both are not in 'interfaces'")

        if all_ok:
            self.logger.info("All specified CAN interfaces are functioning correctly on all nodes.")
            self.send_google_chat_notification("All specified CAN interfaces are functioning correctly on all nodes.")
        else:
            self.logger.warning("One or more CAN interfaces have reported issues on some nodes.")
            self.send_google_chat_notification("One or more CAN interfaces have reported issues on some nodes.")



        
