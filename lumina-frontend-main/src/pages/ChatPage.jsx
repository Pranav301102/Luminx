// Import React state hook for managing form input, response text, loading state, and errors
import { useState } from "react";
// Import API helper functions for normal and streaming text generation requests
import { generateText, streamGenerate } from "../api/requestsApi";
// Import reusable error display component
import ErrorBanner from "../components/common/ErrorBanner";

export default function ChatPage() {
  // Stores the user's input prompt
  const [prompt, setPrompt] = useState("");

  // Stores the model/backend response shown in the Response card
  const [responseText, setResponseText] = useState("");

  // Tracks whether a generation request is currently running
  const [loading, setLoading] = useState(false);

  // Controls whether the request uses streaming mode or normal non-streaming mode
  const [streamMode, setStreamMode] = useState(false);

  // Stores any error message displayed by ErrorBanner
  const [error, setError] = useState("");

  // Handles form submission when the user clicks "Submit Prompt"
  async function handleSubmit(e) {
    // Prevent the browser from refreshing the page on form submit
    e.preventDefault();

    // Do not submit empty prompts
    if (!prompt.trim()) return;

    // Reset UI state before starting a new generation request
    setLoading(true);
    setResponseText("");
    setError("");

    try {
      if (streamMode) {
        // Person 1:
        // Confirm the backend streaming endpoint contract and chunk format.
        // Each received chunk is appended to the previous response text.
        await streamGenerate(prompt, (chunk) => {
          setResponseText((prev) => prev + chunk);
        });
      } else {
        // Person 1:
        // Confirm the non-streaming generation response fields.
        // Expected result may contain an "output" field.
        const result = await generateText({
          prompt,
          stream: false,
        });

        // Display the generated output if available.
        // If not, show the full JSON response for debugging.
        setResponseText(result.output || JSON.stringify(result, null, 2));
      }
    } catch (err) {
      // Log the full error for debugging in the browser console
      console.error(err);

      // Show a simple user-facing error message
      setError("Generation failed.");
    } finally {
      // Stop loading state after success or failure
      setLoading(false);
    }
  }

  return (
    <div className="page-section">
      {/* Page header */}
      <div className="page-title-row">
        <div>
          <h2>Chat</h2>
          <p>Submit prompts and inspect model output.</p>
        </div>
      </div>

      {/* Display error message only when error state is not empty */}
      <ErrorBanner message={error} />

      {/* Prompt input form */}
      <form className="card" onSubmit={handleSubmit}>
        <label className="input-label">Prompt</label>

        {/* Text area where the user enters a prompt */}
        <textarea
          rows="7"
          placeholder="Enter prompt here..."
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />

        <div className="controls-row">
          {/* Streaming mode toggle */}
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={streamMode}
              onChange={(e) => setStreamMode(e.target.checked)}
            />
            Use streaming mode
          </label>

          {/* Submit button is disabled while request is running */}
          <button type="submit" disabled={loading}>
            {loading ? "Generating..." : "Submit Prompt"}
          </button>
        </div>
      </form>

      {/* Response display area */}
      <div className="card">
        <h3>Response</h3>

        {/* 
          <pre> preserves formatting, line breaks, and spacing,
          which is useful for model output and JSON debugging.
        */}
        <pre>{responseText || "No response yet."}</pre>
      </div>
    </div>
  );
}
