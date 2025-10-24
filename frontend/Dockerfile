FROM node:20-slim

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Expose port
EXPOSE 5174

# Run the application
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

