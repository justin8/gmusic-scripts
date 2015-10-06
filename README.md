Need to populate 'settings' file in json format with the following:

`acoustid_api_key` from https://acoustid.org/api-key

And for web server and youtube searching capabilities, the following are also needed:

`app_secret_key` Used to sign cookies. Can be whatever. Something complex.
`user_agent` is whatever you want. I think.

 Google developer console under APIs & Auth -> Credentials

`google_api_key` is the 'API Keys' listing. used for youtube searches

Under the 'OAuth 2.0 client IDs' section:
`client_id` is never what you think it is; the client ID that google expects is not what they provide in the 'client ID' field of their website. You want it in the email format for some ungodly reason. I.E if they provide you with 'abcd123re.apps.googleusercontent.com' you probably want 'abcd123re@developer.gserviceaccount.com
`redirect_uri` is set per client ID
