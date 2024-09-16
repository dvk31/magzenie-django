FROM node:14

# Install necessary tools
RUN apt-get update && apt-get install -y postgresql-client

# Install Supabase CLI
RUN npm install -g supabase

# Copy your scripts
COPY create_supabase_instance.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/create_supabase_instance.sh

# Install Express.js for the API
RUN npm install express

# Copy your API server file
COPY server.js /app/server.js

WORKDIR /app

CMD ["node", "server.js"]