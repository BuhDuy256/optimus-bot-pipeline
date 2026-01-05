##### 1. Scarper: Pull ≥ 30 articles from support.optisigns.com.

![alt text](image.png)

##### 2. Scarper: Convert each article to clean Markdown.

![alt text](image-1.png)

##### 3. Uploader: Upload Markdown files to OpenAI Vector Store via OpenAI API.

###### Result 1:

![alt text](image-2.png)

=> The result is incorrect; the AI responded based on its default knowledge.
=> Error detected: 
  - The vector store does not contain data related to YouTube.
  => The error originates from "scraper.py" because, by default, it only crawls 30 articles.
