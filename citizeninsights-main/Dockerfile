FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code to the working directory
COPY . .

# Expose the port that Streamlit will run on
EXPOSE 8051

# Command to run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8051", "--server.enableCORS=false"]