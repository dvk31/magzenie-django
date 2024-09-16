# mock_openai_client.py
import logging

logger = logging.getLogger(__name__)

class MockOpenAIClient:
    class ImagesResponse:
        def __init__(self, data):
            self.data = data

    class Image:
        def __init__(self, url):
            self.url = url

    class Images:
        @staticmethod
        def generate(model, prompt, size, quality, n):
            # Mimic the structure of the OpenAI response
            image_data = MockOpenAIClient.Image(url='https://oaidalleapiprodscus.blob.core.windows.net/private/org-zIN9jIDffMYvGBK8YjGihY3V/user-d8BVmX8pjzt8Ui5ioNiYlloc/img-AaYsV1inA4AugOyt1Ym10Zs0.png?st=2024-04-28T07%3A05%3A12Z&se=2024-04-28T09%3A05%3A12Z&sp=r&sv=2021-08-06&sr=b&rscd=inline&rsct=image/png&skoid=6aaadede-4fb3-4698-a8f6-684d7786b067&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2024-04-27T19%3A26%3A35Z&ske=2024-04-28T19%3A26%3A35Z&sks=b&skv=2021-08-06&sig=dzpTSnuffw/YtbjTYCfBLrftP3EdBjoMwcdMcz5c41A%3D')
            return MockOpenAIClient.ImagesResponse(data=[image_data])

    @property
    def images(self):
        return self.Images()