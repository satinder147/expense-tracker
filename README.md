# expense-tracker
With multiple bank accounts and credit cards, I was loosing track of the transactions I was making in a month.  
Already available ways to keep track of the all the transactions.  
1. Some apps want me to manually add the transactions: To much effort and less reliable.
2. Manually go to each bank's website and see the transactions: Even more effort but reliable. 
3. Apps like CRED: Need email read access, are you kidding me?

Here comes my not very elegant solution that takes in the least amount of effort, if we don't add up the effort that went in to create this project and decorating this README.

## Architecture
![Alt text](expense-tracker.png?raw=true "Architecture")

### How did I do this?
1. I bought a domain (satindersh.com). Got this domain verified with AWS SES. 
2. Added `inbound-smtp.us-east-1.amazonaws.com.` as my MX record in my DNS setting on my Domain providers website. 
3. Now any email sent with domain `satindersh.com` will be forwarded to `inbound-smtp.us-east-1.amazonaws.com` and since my domain is verified with aws, it know to which account my email should be forwarded. 
```
Email receiving only works in a few regions, be carefull with that. The created identity needs to be in one of those regions (one example is us-east-1)
```
4. Now I gave permissions to AWS SES to write my emails to a s3 bucket. 
5. A lambda function is invoked on inserts into this bucket. This lambda function updates google keeps with all the transactions I made in the past 1 month. 


### How to setup the lambda function?
1. Create a deployment-package.zip with the required dependencies by following these [instructions](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html) or just add your lambda function to the already existing deployment-package.zip in this repo using `zip -g deployment-package.zip lambda_function.py`
2. Upload the deployment package in aws lambda.
3. In the configuration tab, add the environment variables(username and app_password)
4. Add a trigger to trigger the lambda function on S3 putobjects.

## What did I acheive
1. I get to see a pretty list of the transactions
2. I learnt a lot!!!!!

## Problems
1. I can't provide this facility to anyone else, in a way I need their email access. 
2. Deploying this is a **PAIN**. This one probably can be solved with `terraform` or `aws cloud formation`. 
3. For new cards, I need to add a new forward rule to my gmail account and update my lambda function. The latter can be solved with a configuration file. Something even better will be to train a ml model to automatically extract amount spent, vendor, date of transaction, card number from the email. 

## Any ideas to improve the solution 