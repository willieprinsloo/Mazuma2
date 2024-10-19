curl -X POST https://works.reboxed.co/api/Product/PriceUpdate \
     -H "Content-Type: application/json" \
     -d '{
           "Products": [
             {
               "SKU": "ABC1234",
               "Reference": "122440",
               "Price": 10.99,
               "Tag": ""
             }
           ],
           "AuthorizationToken": "4d1aa44d211641a48da9ae269ff68975"
         }'

SERVrbxd20(*)S
cd /root/synccatalog/mazumav2
scp -i ~/.ssh/id_rsa * root@143.198.241.81:/root/works.reboxed.co 
systemctl restart reboxed.service 

Old server
sshpass -p 'SERVrbxd20(*)S' ssh -o StrictHostKeyChecking=no root@138.68.154.225

{'LinnworksUniqueIdentifier': 'b063fff4-f5bc-44b4-8bbf-83353e9443b0', 'Email': 'systems@reboxed.co', 'AccountName': 'Reboxed'}
Application Id:
3a90f9e2-315d-49f5-ad24-d4354c544af0

tail -n 50 -f app.log
ssh root@143.198.241.81

sudo journalctl -u reboxed.service -n 50
