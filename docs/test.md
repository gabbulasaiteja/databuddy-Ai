# Testing & Deployment Guide

## 1. Local Setup & Execution
Because Next.js is a full-stack framework, your frontend and backend run together in one process. You do not need two separate servers.
* **Install dependencies:** `npm install`
* **Run development server:** `npm run dev`
* **Access the app:** Open `http://localhost:3000` in your browser.

## 2. Testing the Data Pipeline
1. **The Prompt Test:** Type "Create a table called test_logs with an ID and Message" in the chatbot.
2. **The Visual Test:** Watch the SQL Panel. Did the code appear? Did the terminal log a success message?
3. **The Ground Truth Test:** Open your actual Neon.tech web console. Navigate to the "Tables" section. Verify that `test_logs` was physically created in the AWS database.

## 3. Production Deployment (Vercel)
Vercel is the creator of Next.js and is the fastest way to deploy this full-stack application.
1. Install the Vercel CLI: `npm i -g vercel`
2. Authenticate: `vercel login`
3. Run the deployment command from your project root: `vercel`
4. Add your Environment Variables:
   * The CLI will prompt you to set up the project. Once deployed, go to the Vercel Dashboard.
   * Add your `DATABASE_URL` (Neon) and `OPENAI_API_KEY` in the project settings -> Environment Variables.
5. Re-deploy for production: `vercel --prod`