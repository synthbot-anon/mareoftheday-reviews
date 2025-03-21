import argparse
import asyncio
from typing import AsyncGenerator

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
import requests
from horsona.config import load_indices, load_llms
from horsona.interface import oai
from horsona.llm.base_engine import AsyncLLMEngine
from horsona.llm.chat_engine import AsyncChatEngine

load_dotenv()

llms = load_llms()
indices = load_indices()

profile_data = requests.get("https://raw.githubusercontent.com/effusiveperiscope/mare-of-the-day/refs/heads/main/src/app/profiles.json").json()
profiles = [
    {"name": key, "profile": value["profile"], "quotes": value["quotes"]}
    for key, value in profile_data.items()
]

REVIEW_GUIDELINES = """
### Core Understanding
- **Story Comprehension**: Demonstrates thorough understanding of the plot, characters, and themes without unnecessary summary
- **Contextual Understanding**: Places the work within broader literary/genre context and author's body of work

### Analytical Approach
- **Analysis Depth**: Goes beyond surface observations to explore underlying meaning
- **Critical Insights**: Offers unique perspectives that enhance reader's understanding of the work
- **Balanced Perspective**: Acknowledges both strengths and weaknesses with fair consideration

### Persuasive Elements
- **Persuasive Arguments**: Supports judgments with clear reasoning and evidence from the text
- **Review Credibility**: Establishes trustworthiness through consistent, well-supported evaluations
- **Specific Examples**: References concrete moments or elements from the work to illustrate points

### Personal Elements
- **Personal Connection**: Articulates how the work resonated emotionally or intellectually with the reviewer
- **Emotional Resonance**: Communicates genuine emotional responses to the work's impact
- **Relatable Examples**: Uses relevant comparisons that help readers connect to the reviewer's experience
- **Authentic Voice**: Maintains a distinctive, honest perspective that reflects the reviewer's personality

### Technical Assessment
- **Genre Awareness**: Shows understanding of genre conventions and how the work upholds or subverts them
- **Educational Value**: Provides insights that deepen the reader's appreciation and understanding

### Structural Elements
- **Logical Flow**: Progresses naturally from point to point with smooth transitions
- **Focused Points**: Emphasizes key observations without digressions or tangents

### Additional Elements
- **Euphemistic Language**: Uses indirect expressions to discuss sensitive content respectfully
- **Implied Content**: Suggests dimensions of the work without explicitly stating everything
- **Reader Intrigue**: Creates curiosity that motivates readers to discover the work themselves
- **Humor**: Employs wit and humor to make the review entertaining while informative

### Ultimate Goal
- **Reader Engagement**: Captures and maintains reader interest throughout the review
- **Engaging Review**: Creates a compelling, informative, and enjoyable reading experience that serves its audience
"""


class ReviewerEngine(AsyncChatEngine):
    def __init__(
        self,
        underlying_llm: AsyncLLMEngine,
        profile: dict,
        conversational=False,
        **kwargs,
    ) -> None:
        super().__init__(conversational, **kwargs)
        self.underlying_llm = underlying_llm
        self.profile = profile

    async def query(self, **kwargs) -> AsyncGenerator[str, None]:
        story = "\n\n".join(
            [x["content"] for x in kwargs["messages"] if "content" in x]
        )

        initial_review = await self.underlying_llm.query_block(
            "md",
            REVIEWER=self.profile,
            STORY=story,
            REVIEW_GUIDELINES=REVIEW_GUIDELINES,
            TASK=(
                "- Take on the personality of REVIEWER that has just read the fictional STORY.\n"
                "- As REVIEWER, write a short (1-2 paragraph) newspaper-style review of the STORY based on how REVIEWER would react.\n"
                "- Use the REVIEW_GUIDELINES to inform your review.\n"
                "- Make it clear that you read the STORY, but please write a spoiler-free review. You can describe general premises, but avoid revealing major plot points.\n"
                "- Remember that part of your review should discuss what audiences may find the story entertaining.\n"
                "- Make your review entertaining and fitting to the personality and experiences of REVIEWER.\n"
                "- Strive to provide a balanced review; consider REVIEWER's preferences and values. She may not like every story!\n"
            ),
        )

        refined_review = await self.underlying_llm.query_block(
            "md",
            REVIEWER=self.profile,
            STORY=story,
            REVIEW=initial_review,
            TASK=(
                "Provide a cleaned up version of the REVIEW. To clean up the REVIEW:\n"
                "- Make sure all of the text is in-character for REVIEWER.\n"
                "- Do not include an assent like 'Okay, here's my review' or 'Here is a review'.\n"
                "- Use common 'pony'-isms: e.g. 'anypony' or 'everypony' instead of 'anybody' or 'everybody', 'hoof' instead of 'hand'.\n"
                "- Make sure the review isn't meta. Do not mention things that suggest the existence of Friendship is Magic as a television show, "
                "and make sure show-relevant references are treated as fictional versions of real places/characters/etc.\n"
            ),
        )

        formatted_review = await self.underlying_llm.query_block(
            "html",
            REVIEW=refined_review,
            TASK=(
                "- Format the REVIEW as html. Make it pretty.\n"
                "- Leave the exact content of the review intact, verbatim. Only change the formatting.\n"
                "- Do not use semantic tags like <article> or <code>.\n"
                "- Do not include any titles or headers.\n"
                "- Feel free to use italics, bold, and other formatting to make the review more readable, scannable, and engaging.\n"
            ),
        )

        yield formatted_review


async def main():
    parser = argparse.ArgumentParser(description='Mare of the Day Review Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host address to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000, help='Port to listen on (default: 8000)')
    args = parser.parse_args()

    app = FastAPI(title="Mare of the Day Reviews")
    app.include_router(oai.api_router)

    for profile in profiles:
        reviewer = ReviewerEngine(llms["reasoning_llm"], profile)
        oai.add_llm_engine(reviewer, f"{profile['name']}")

    config = uvicorn.Config(app, host=args.host, port=args.port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
