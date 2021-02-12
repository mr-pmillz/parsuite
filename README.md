# Parsuite

Simple modular framework to support quick creation of file parsers in
Python. See the wiki page for information on creating modules.

I threw this together because I got tired of repeatedly grepping out
the same content for common outputs produced when gunning through
vulnerability assessements and penetration tests. The interface is
extremely primitive but gets the job done, and was written with 
a minimal understanding of argparse. I intend to go back and revisit
it in the future.

# Installation (Python Version >= 3.7)

```
git clone https://github.com/arch4ngel/parsuite
cd parsuite
pip3 install -r requirements.txt
```

## Adding to PATH (Debian)

I use Parsuite enough to add it to my PATH variable like this:

```
mkdir ~/bin
ln -s /path/to/parsuite.py ~/bin/parsuite
```

# Usage

## Listing Modules

Issue the `--help` flag with no arguments. Example:

```
parsuite --help
```

## Getting Module Help

After supplying a module, issue the `--help` flag and help for the specified
module will be returned. Example:

```
parsuite xml_dumper --help
```

# A Note on Output

Output that is unrelated to the parsed content is written to `stderr`. This
allows users to easily redirect the desired content to a file or suppress
error messages.

# Current Modules

|Module|Description|
|--|--|
|bloodhound_property_manager|Modify each BloodHound JSON file and add a property toeach object|
|bloodhound_property_manager_neo4j|Accept a CSV file and upate a series of BloodHound nodes in a given Neo4j database.|
|burp_info_extractor|Input an XML file containing Burp items and dump each  transaction to a directory.|
|burp_items_to_authmatrix|Parse an XML file containing Burp items and return a JSON statefile for AuthMatrix. Each item element of the input file must contain a "username" child element and one or more "role" child elements. WARNING: THE CHILD AND USERNAME ELEMENTS MUST BE ADDED TO EACH ITEM MANUALLY!!!|
|burp_to_authmatrix|Parse cookies from the results table of a Burp Intruder attack and translate them to an Authmatrix state file for those users. Warning:  This tool assumes that the username is in Payload1. Also make sure that  invalid records are removed from the table file, otherwise they will  be translated and added to the JSON file.|
|crt_sh|Query crt.sh and dump output to disk|
|csharp_hexarray_parser|Parse C# shellcode from payload files generated by Metsploit or Cobalt Strike. Useful when embedding content in other formats.|
|encoder|Encode a series of values or contents of files. WARNING:  files are slurped and encoded as a whole.|
|enum4linux_dumper|Dump groups and group memberships to disk, using the filesystem as as basic database for simple searching using grep and other mechanism.|
|hash_linker|Map cleartext passwords recovered from password cracking back  to uncracked values.|
|hc_kerberoast_dumper|Iterate over each cracked credential in an output file generated by HashCat that contains cracked Kerberos tickets and return each record in <spn>:<password> format|
|ip_expander|Expand a series of IPv4/6 ranges into addresses.|
|ldap_dissection_xml_dumper|Dump LDAP objects from a file exported by Wireshark in PDML format.|
|line_filter|Remove lines found in bad files from lines found in good files and write the resultant set of good lines to an output file.|
|moz_cookies_parser|Accept an Firefox cookie file (SQLite3) and dump each record in CSV format. strLastAccessed and strCreationTime are added to each record to help find the freshest cookies. The final column contains the constructed cookie.|
|nessus_api_host_dumper|Extract affected hosts from the Nessus REST API. Useful in situations when running a large scan or you don't want to deal with exporting the .nessus file for use with the `xml_dumper` module.|
|nessus_output_dumper|Parse a Nessus file and dump the contents to disk by: risk_factor > plugin_name|
|nmap_smb_security_mode_dumper|Dump hosts to a file containing the security mode discovered by smb-security-mode.|
|nmap_ssl_name_dumper|Accept a XML file generated by Nmap and write SSL certificate information to stdout|
|nmap_to_sqlite|Convert XML files generated by NMap to an SQLite database.|
|nmap_top_port_dumper|Parse the Nmap services file and dump the most commonly open ports.|
|nmap_xml_service_dumper|Accept a XML file generated by Nmap and write the output to a local directory structure, organized by service, for easy browsing.|
|ntlm_hasher|NTLM hash a value.|
|ntlmv2_dumper|Parse files containing NTLMv2 hashes in the common format produced by Responder and Impacket and dump them to stdout. Messages printed that are not hashes are dumped to stderr. Use the -du flag to disable uniquing of username/domain/password combinations.|
|payload_inserter|Define an insertion point (signature) within a template file and replace the line with a payload from a distinct file. Useful in situations where an extremely long payload needs to be inserted, such as when working with hex shellcode for stageless payloads.|
|prettyfi_json|Pretty print a JSON object to stdout.|
|rdp_sec_check_dumper|Parse output from an rdp_sec_check scan and dump output to individual files relative to issue, such as "nla_not_enforced."|
|recon_ng_contact_dumper|Parse an SQLite3 database generated by recon-ng and dump the contacts out in simple string format|
|socket_dumper|IPv4 ONLY! Accept a list of sockets and output three files:  unique list of IP addresses, unique list of ports, unique list of fqdns|
|string_randomizer|Accept a string as input and replace a template with random values.|
|templatizer|Accept a series of text templates and update their values. It ingests a CSV file, making the values of each field available to each template.|
|urlcrazy_to_csv|Convert URLCrazy output to CSV|
|xml_dumper|Dump hosts and open ports from multiple masscan, nmap, or nessus files. A generalized abstraction layer is used to produce objects that align with the Nmap XML structure since it has the most comprehensive XSD file.|
