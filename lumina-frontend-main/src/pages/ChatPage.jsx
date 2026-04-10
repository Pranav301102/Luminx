import { useState } from "react";
import { generateText, streamGenerate } from "../api/requestsApi";
import ErrorBanner from "../components/common/ErrorBanner";

export default function ChatPage() {
  const [prompt, setPrompt] = useState("");
  const [responseText, setResponseText] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamMode, setStreamMode] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();

    if (!prompt.trim()) return;

    setLoading(true);
    setResponseText("");
    setError("");

    try {
      if (streamMode) {
        // TODO(Person 1): confirm streaming endpoint contract and chunk format
        await streamGenerate(prompt, (chunk) => {
          setResponseText((prev) => prev + chunk);
        });
      } else {
        // TODO(Person 1): confirm non-streaming generation response fields
        const result = await generateText({
          prompt,
          stream: false,
        });

        setResponseText(result.output || JSON.stringify(result, null, 2));
      }
    } catch (err) {
      console.error(err);
      setError("Generation failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-section">
      <div className="page-title-row">
        <div>
          <h2>Chat</h2>
          <p>Submit prompts and inspect model output.</p>
        </div>
      </div>

      <ErrorBanner message={error} />

      <form className="card" onSubmit={handleSubmit}>
        <label className="input-label">Prompt</label>
        <textarea
          rows="7"
          placeholder="Enter prompt here..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />

        <div className="controls-row">
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={streamMode}
              onChange={(e) => setStreamMode(e.target.checked)}
            />
            Use streaming mode
          </label>

          <button type="submit" disabled={loading}>
            {loading ? "Generating..." : "Submit Prompt"}
          </button>
        </div>
      </form>

      <div className="card">
        <h3>Response</h3>
        <pre>{responseText || "No response yet."}</pre>
      </div>
    </div>
  );
}