# ShipShape — Your Friendly DevOps Troubleshooter

ShipShape is a calm, read-only AI helper for Linux, Docker, Git, and GitHub Actions errors. The browser calls an API Gateway HTTPS endpoint; Lambda invokes OpenAI's Responses API using a backend-only API key. It never runs suggested commands or changes infrastructure.

## Local setup

Prerequisites: Node.js 20+, Python 3.12+, AWS CLI, AWS SAM CLI, an OpenAI API key with credits, and GitHub/Amplify access for hosting.

```bash
cd frontend
npm install
cp ../.env.example .env.local
# edit .env.local with the deployed API URL
npm run dev
```

Run backend tests with `python -m unittest discover -s backend/tests -p 'test_*.py'`.

## Deploy the backend

First configure AWS credentials using your normal approved profile. These commands create only the resources in `template.yaml`; they do not delete resources or touch unrelated infrastructure.

```bash
sam build
sam deploy --guided
```

When prompted, set `FrontendOrigin` to the exact Amplify HTTPS origin, `OpenAIApiKey` to your OpenAI API key, and `OpenAIModel` to a model available to your account. SAM prints `ApiUrl`; put that URL in `frontend/.env.local` as `VITE_API_URL`, then build the frontend. Never commit the API key or put it in a `VITE_*` variable.

## Amplify Hosting

Create or connect an Amplify Hosting app to this GitHub repository, set the build setting to the included `amplify.yml`, and add the environment variable `VITE_API_URL` with the API URL. Amplify’s default domain is HTTPS. After the first deploy, if the origin differs from the one used for the Lambda stack, update the `FrontendOrigin` parameter and redeploy the stack.

## Verification

Do not treat a successful deployment as proof of AI access. Verify the endpoint with a harmless sample after deployment:

```bash
curl -i -X POST "$API_URL/troubleshoot" -H 'content-type: application/json' \
  --data '{"error_text":"docker: permission denied while trying to connect to the Docker daemon socket"}'
```

Then open the Amplify HTTPS URL and run the same scenario in the UI. Record the actual API URL, Amplify URL, model/Region, and tested scenarios in your release notes; this README intentionally does not invent URLs before deployment.

## Cleanup

Only after confirming the stack name and that it is this project, remove the SAM stack with `sam delete --stack-name <stack-name>`. Remove the Amplify app from its console if it is no longer needed. Review any retained CloudWatch logs. These are explicit cleanup actions; ShipShape does not run them automatically.

## Security notes

No AWS or OpenAI credentials belong in browser code, `.env` files committed to Git, or logs. The OpenAI key is configured only on Lambda. CORS is restricted to `FrontendOrigin`. Model output is displayed as advice only. For production, prefer AWS Secrets Manager or another managed secret store rather than a plain CloudFormation parameter.
