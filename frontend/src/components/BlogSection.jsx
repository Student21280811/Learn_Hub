import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function BlogSection() {
    const [posts, setPosts] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchBlogPosts();
    }, []);

    const fetchBlogPosts = async () => {
        try {
            const response = await axios.get(`${API}/blog/posts?limit=3`);
            setPosts(response.data);
        } catch (error) {
            console.error('Failed to fetch blog posts:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <section className="blog-section">
                <div className="blog-container">
                    <div className="blog-skeleton">Loading...</div>
                </div>
            </section>
        );
    }

    if (!posts || posts.length === 0) {
        return null; // Don't show section if no posts
    }

    return (
        <section className="blog-section">
            <div className="blog-container">
                <div className="blog-header">
                    <h2>📚 Latest from Our Blog</h2>
                    <p>Discover insights, tips, and success stories</p>
                </div>

                <div className="blog-grid">
                    {posts.map((post) => (
                        <div key={post.id} className="blog-card">
                            {post.cover_image && (
                                <div className="blog-image">
                                    <img src={post.cover_image} alt={post.title} />
                                </div>
                            )}

                            <div className="blog-content">
                                <span className="blog-category">{post.category}</span>
                                <h3>{post.title}</h3>
                                <p className="blog-excerpt">{post.excerpt}</p>

                                <div className="blog-meta">
                                    <span>{new Date(post.published_at).toLocaleDateString()}</span>
                                    <span>👁 {post.views || 0} views</span>
                                </div>

                                {post.course_id && (
                                    <Link to={`/courses/${post.course_id}`} className="blog-link">
                                        View Course <ExternalLink size={14} />
                                    </Link>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
