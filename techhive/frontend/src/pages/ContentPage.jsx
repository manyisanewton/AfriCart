import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { contentAPI, supportAPI } from "../services/api";
import NotFoundPage from "./NotFoundPage";
import "../styles/contentPage.css";

function sanitizeCmsHtml(html = "") {
  return String(html)
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, "")
    .replace(/\son\w+="[^"]*"/gi, "")
    .replace(/\son\w+='[^']*'/gi, "")
    .replace(/javascript:/gi, "");
}

export default function ContentPage() {
  const location = useLocation();
  const [page, setPage] = useState(null);
  const [status, setStatus] = useState("loading");
  const [submitState, setSubmitState] = useState("idle");
  const [submitMessage, setSubmitMessage] = useState("");
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone_number: "",
    subject: "",
    message: "",
    product_name: "",
    product_url: "",
    reason: "",
    order_number: "",
    company_name: "",
    campaign_goal: "",
    budget_range: "",
    preferred_timeline: "",
  });

  useEffect(() => {
    let active = true;

    async function loadPage() {
      setStatus("loading");
      try {
        const response = await contentAPI.resolvePage(location.pathname);
        if (!active) return;
        const item = response?.data?.item || null;
        if (!item) {
          setPage(null);
          setStatus("not_found");
          return;
        }
        setPage(item);
        setStatus("ready");
        if (item.meta_title) {
          document.title = item.meta_title;
        }
      } catch (error) {
        if (!active) return;
        if (error?.response?.status === 404) {
          setPage(null);
          setStatus("not_found");
          return;
        }
        setPage(null);
        setStatus("error");
      }
    }

    loadPage();
    return () => {
      active = false;
    };
  }, [location.pathname]);

  useEffect(() => {
    setSubmitState("idle");
    setSubmitMessage("");
    setFormData({
      name: "",
      email: "",
      phone_number: "",
      subject: "",
      message: "",
      product_name: "",
      product_url: "",
      reason: "",
      order_number: "",
      company_name: "",
      campaign_goal: "",
      budget_range: "",
      preferred_timeline: "",
    });
  }, [page?.page_key]);

  const safeHtml = useMemo(() => sanitizeCmsHtml(page?.content || ""), [page?.content]);
  const interactiveMode = page?.page_key === "report_a_product"
    ? "report_product"
    : page?.page_key === "advertise_with_us"
      ? "advertise"
      : null;

  function updateField(event) {
    const { name, value } = event.target;
    setFormData((current) => ({ ...current, [name]: value }));
  }

  async function submitInteractiveForm(event) {
    event.preventDefault();
    if (!page || !interactiveMode) return;

    setSubmitState("submitting");
    setSubmitMessage("");

    try {
      const payload = interactiveMode === "report_product"
        ? {
            name: formData.name.trim(),
            email: formData.email.trim(),
            phone_number: formData.phone_number.trim(),
            subject: formData.subject.trim() || `Product report: ${formData.product_name.trim() || "Listing concern"}`,
            message: formData.message.trim(),
            category: "product_report",
            context_data: {
              page_key: page.page_key,
              product_name: formData.product_name.trim(),
              product_url: formData.product_url.trim(),
              reason: formData.reason.trim(),
              order_number: formData.order_number.trim(),
            },
          }
        : {
            name: formData.name.trim(),
            email: formData.email.trim(),
            phone_number: formData.phone_number.trim(),
            subject: formData.subject.trim() || `Advertising inquiry from ${formData.company_name.trim() || formData.name.trim()}`,
            message: formData.message.trim(),
            category: "advertising",
            context_data: {
              page_key: page.page_key,
              company_name: formData.company_name.trim(),
              campaign_goal: formData.campaign_goal.trim(),
              budget_range: formData.budget_range.trim(),
              preferred_timeline: formData.preferred_timeline.trim(),
            },
          };

      await supportAPI.createTicket(payload);
      setSubmitState("success");
      setSubmitMessage(
        interactiveMode === "report_product"
          ? "Your product report has been submitted. Our team will review it."
          : "Your advertising inquiry has been submitted. Our team will get back to you."
      );
    } catch (error) {
      const detail =
        error?.response?.data?.error?.message ||
        error?.response?.data?.detail ||
        "We could not submit your request right now.";
      setSubmitState("error");
      setSubmitMessage(detail);
    }
  }

  if (status === "loading") {
    return (
      <section className="content-page-shell">
        <div className="content-page-card">
          <p className="content-page-eyebrow">Content</p>
          <h1>Loading page...</h1>
          <p className="content-page-copy">Please wait while we load this page.</p>
        </div>
      </section>
    );
  }

  if (status === "not_found") {
    return <NotFoundPage />;
  }

  if (status === "error") {
    return (
      <section className="content-page-shell">
        <div className="content-page-card">
          <p className="content-page-eyebrow">Content unavailable</p>
          <h1>We could not load this page</h1>
          <p className="content-page-copy">
            The content may be unavailable right now. Please try again in a moment or go back to the storefront.
          </p>
          <Link className="content-page-link" to="/">Return home</Link>
        </div>
      </section>
    );
  }

  return (
    <section className="content-page-shell">
      <div className="content-page-card">
        <div className="content-page-header">
          <p className="content-page-eyebrow">{page.page_type || "Content page"}</p>
          <h1>{page.title}</h1>
          {page.excerpt && <p className="content-page-copy">{page.excerpt}</p>}
        </div>

        <div className="content-page-body" dangerouslySetInnerHTML={{ __html: safeHtml }} />

        {interactiveMode && (
          <div className="content-page-form-shell">
            <div className="content-page-form-header">
              <h2>{interactiveMode === "report_product" ? "Submit a product report" : "Send an advertising inquiry"}</h2>
              <p>
                {interactiveMode === "report_product"
                  ? "Share the listing details and why the product should be reviewed."
                  : "Tell us about your brand, campaign goal, and timeline so our team can follow up."}
              </p>
            </div>

            <form className="content-page-form" onSubmit={submitInteractiveForm}>
              <div className="content-page-form-grid">
                <label>
                  <span>Name</span>
                  <input name="name" value={formData.name} onChange={updateField} required />
                </label>
                <label>
                  <span>Email</span>
                  <input type="email" name="email" value={formData.email} onChange={updateField} required />
                </label>
                <label>
                  <span>Phone number</span>
                  <input name="phone_number" value={formData.phone_number} onChange={updateField} />
                </label>
                <label>
                  <span>Subject</span>
                  <input name="subject" value={formData.subject} onChange={updateField} placeholder="Optional subject" />
                </label>

                {interactiveMode === "report_product" ? (
                  <>
                    <label>
                      <span>Product name</span>
                      <input name="product_name" value={formData.product_name} onChange={updateField} required />
                    </label>
                    <label>
                      <span>Product URL</span>
                      <input name="product_url" value={formData.product_url} onChange={updateField} placeholder="/products/example-slug" />
                    </label>
                    <label>
                      <span>Reason</span>
                      <input name="reason" value={formData.reason} onChange={updateField} placeholder="Counterfeit, unsafe, misleading..." required />
                    </label>
                    <label>
                      <span>Order number</span>
                      <input name="order_number" value={formData.order_number} onChange={updateField} />
                    </label>
                  </>
                ) : (
                  <>
                    <label>
                      <span>Company name</span>
                      <input name="company_name" value={formData.company_name} onChange={updateField} required />
                    </label>
                    <label>
                      <span>Campaign goal</span>
                      <input name="campaign_goal" value={formData.campaign_goal} onChange={updateField} placeholder="Brand awareness, launch, traffic..." required />
                    </label>
                    <label>
                      <span>Budget range</span>
                      <input name="budget_range" value={formData.budget_range} onChange={updateField} placeholder="KES 50,000 - 150,000" />
                    </label>
                    <label>
                      <span>Preferred timeline</span>
                      <input name="preferred_timeline" value={formData.preferred_timeline} onChange={updateField} placeholder="Next month, Q3 launch..." />
                    </label>
                  </>
                )}
              </div>

              <label className="content-page-form-full">
                <span>Details</span>
                <textarea
                  name="message"
                  rows="6"
                  value={formData.message}
                  onChange={updateField}
                  placeholder={interactiveMode === "report_product" ? "Describe the product issue in detail..." : "Describe your campaign, audience, and expected placements..."}
                  required
                />
              </label>

              {submitMessage && (
                <div className={`content-page-form-feedback content-page-form-feedback--${submitState}`}>
                  {submitMessage}
                </div>
              )}

              <div className="content-page-form-actions">
                <button type="submit" disabled={submitState === "submitting"}>
                  {submitState === "submitting" ? "Submitting..." : interactiveMode === "report_product" ? "Submit report" : "Send inquiry"}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </section>
  );
}
