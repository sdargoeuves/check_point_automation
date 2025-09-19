#!/usr/bin/env python3
"""
Example of using script deployment functionality.
"""

import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from checkpoint_automation import (
    FirewallConfig, 
    SSHConnectionManager, 
    ExpertPasswordManager,
    ScriptDeploymentManager
)


def main():
    """Example of complete script deployment workflow."""
    
    # Configuration
    config = FirewallConfig(
        ip_address="10.194.58.200",  # Update this IP
        username="admin",
        password="admin",
        expert_password="password123"  # Update this password
    )
    
    # Sample initial configuration script
    initial_config_script = """#!/bin/bash
# Script to generate first_wizard.conf

# Find the hash for admin password and maintenance
echo "Getting admin password hash..."
admin_hash=$(dbget passwd:admin:passwd)
echo "Admin hash captured: $admin_hash"
echo


MAINTENANCE_PASSWORD="KimK1ys8tfFD3aaao"

echo "Generating maintenance password hash..."

# Pipe the password twice (once for entry, once for confirmation) to grub2-mkpasswd-pbkdf2
maintenance_output=$(echo -e "${MAINTENANCE_PASSWORD}\n${MAINTENANCE_PASSWORD}" | grub2-mkpasswd-pbkdf2)

# Extract the hash as before
maintenance_hash=$(echo "$maintenance_output" | grep "PBKDF2 hash" | awk '{print $NF}')

echo "Maintenance hash generated: ${maintenance_hash:0:50}..."
echo ""

# Create first_wizard.conf file
echo "Creating first_wizard.conf file..."

cat > first_wizard.conf << EOF

# Install Security Gateway.
install_security_gw=true

# Enable DAIP (dynamic ip) gateway.
# Should be "false" if CXL or Security Management enabled
gateway_daip="false"

# Enable/Disable CXL.
gateway_cluster_member=false

# Install Security Management.
install_security_managment=true
install_mgmt_primary=true
install_mgmt_secondary=false

# Provider-1 parameters
install_mds_primary=false
install_mds_secondary=false
install_mlm=false
install_mds_interface=false

# Automatically download and install Software Blade Contracts, security updates, and other important data (highly recommended)
# for more info see sk175504
# possible values: "true" / "false"
download_info="false"

# Automatically download software updates and new features (highly recommended).
download_from_checkpoint_non_security="false"
# Help Check Point improve the product by sending anonymous information.
upload_info="false"
# Help Check Point improve the product by sending core dump files and other relevant crash data
upload_crash_data="false"

# Management administrator configuration
# Set to "gaia_admin" if you wish to use the Gaia 'admin' account.
# Set to "new_admin" if you wish to configure a new admin account.
mgmt_admin_radio="new_admin"

# In case you chose to configure a new Management admin account,
mgmt_admin_name="vagrant"
# Management administrator password
mgmt_admin_passwd="vagrant"

# Management GUI clients
# choose which GUI clients can log into the Security Management
# (e.g. any, 1.2.3.4, 192.168.0.0/24)
# Set to "any" if any host allowed to connect to management
# Set to "range" if range of IPs allowed to connect to management
# Set to "network" if IPs from specific network allowed to connect
# to management
# Set to "this" if it' a single IP
# Must be provided if Security Management installed
mgmt_gui_clients_radio=any
#
# In case of "range", provide the first and last IPs in dotted format
mgmt_gui_clients_first_ip_field=
mgmt_gui_clients_last_ip_field=
#
# In case of "network", provide IP in dotted format and netmask length
# in range 1-32
mgmt_gui_clients_ip_field=
mgmt_gui_clients_subnet_field=
#
# In case of a single IP
mgmt_gui_clients_hostname=

# Secure Internal Communication key, e.g. "aaaa"
# Must be provided, if primary Security Management not installed
ftw_sic_key=

# Management as a service
# optional parameter for security_gateway only
maas_authentication_key=

# Password (hash) of user admin.
# To get hash of admin password from configured system:
# 	dbget passwd:admin:passwd
admin_hash='$admin_hash'

# Default maintenance password (hash)
# To generate a hash of maintenance password - in expert mode:
# 	grub2-mkpasswd-pbkdf2
maintenance_hash='$maintenance_hash'

# Interface name, optional parameter
iface=

ipstat_v4=manually
ipaddr_v4=
masklen_v4=
default_gw_v4=

ipstat_v6=off
ipaddr_v6=
masklen_v6=
default_gw_v6=

# Host Name e.g host123, optional parameter
hostname=cp

# Domain Name e.g. checkpoint.com, optional parameter
domainname=netlab.ipf

timezone='Etc/GMT'

# NTP servers
ntp_primary=

# DNS - IP address of primary, secondary, tertiary DNS servers
primary=1.1.1.1

# Optional parameter, if not specified the default is false
install_security_vsx=
# Optional parameter, if not specified the default is false
reboot_if_required=true


EOF

echo "first_wizard.conf file created successfully!"
echo "File contains:"
echo "- admin_hash='$admin_hash'"
echo "- maintenance_hash='${maintenance_hash:0:50}...'"
echo

echo "Running dry-run to validate configuration..."
echo "   config_system -f first_wizard.conf --dry-run"
echo "===================================================="
config_system -f first_wizard.conf --dry-run
echo "===================================================="
echo

echo "Dry-run completed. Review the output above."
echo "If you are happy with the configuration, run this command:"
echo "config_system -f first_wizard.conf"

echo "Running configuration..."
echo "   config_system -f first_wizard.conf"
echo "===================================================="
config_system -f first_wizard.conf
echo "===================================================="
echo
"""
    
    print("Check Point Script Deployment Example")
    print("=" * 50)
    
    try:
        # Step 1: Connect to firewall
        print(f"Connecting to firewall at {config.ip_address}...")
        ssh_manager = SSHConnectionManager(config, console_log_level="INFO")
        
        if not ssh_manager.connect():
            print("Failed to connect to firewall")
            return False
        
        print("✓ Connected to firewall")
        
        # Step 2: Setup expert password if needed
        print("Setting up expert password...")
        expert_manager = ExpertPasswordManager(ssh_manager)
        
        success, message = expert_manager.setup_expert_password_workflow(config.expert_password)
        if not success:
            print(f"Failed to setup expert password: {message}")
            ssh_manager.disconnect()
            return False
        
        print("✓ Expert password setup completed")
        
        # Step 3: Deploy and execute script
        print("Deploying and executing initial configuration script...")
        script_manager = ScriptDeploymentManager(ssh_manager)
        
        success, output = script_manager.deploy_and_execute_script(initial_config_script)
        
        if success:
            print("✓ Script deployment and execution successful!")
            print("\nScript execution output:")
            print("-" * 60)
            print(output)
            print("-" * 60)
            
            # Check if reboot is needed
            if "reboot" in output.lower() or "connection lost" in output.lower():
                print("\n🔄 Reboot detected in script output")
                print("This is normal for config_system commands")
                print("Handling reboot scenario...")
                
                reboot_success, reboot_message = script_manager.handle_reboot_scenario(max_wait_time=600)
                if reboot_success:
                    print("✓ Successfully handled reboot and reconnected")
                    print("✓ Firewall is back online and responsive")
                else:
                    print(f"⚠️  Reboot handling issue: {reboot_message}")
                    print("You may need to wait longer or check firewall status manually")
        else:
            print(f"✗ Script deployment failed: {output}")
            return False
        
        # Step 4: Cleanup
        ssh_manager.disconnect()
        print("\n✓ All operations completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)