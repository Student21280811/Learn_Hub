import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import Navbar from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { BookOpen, User, Mail, Award } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function PublicProfile({ user: currentUser, logout }) {
    const { id } = useParams();
    const [profile, setProfile] = useState(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        fetchProfile();
    }, [id]);

    const fetchProfile = async () => {
        try {
            const response = await axios.get(`${API}/users/profile/${id}`);
            setProfile(response.data);
        } catch (error) {
            toast.error('User not found or failed to load profile');
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="loading">Loading profile...</div>;
    if (!profile) return <div className="p-8 text-center">User not found</div>;

    return (
        <div className="profile-page min-h-screen bg-gray-50">
            <Navbar user={currentUser} logout={logout} />

            <div className="max-w-5xl mx-auto px-4 py-12 ml-auto mr-auto">
                <div className="grid md:grid-cols-3 gap-8">
                    {/* Sidebar */}
                    <div className="md:col-span-1">
                        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 text-center">
                            <div className="w-32 h-32 rounded-full border-4 border-primary/10 bg-primary/5 mx-auto mb-6 flex items-center justify-center text-4xl font-bold overflow-hidden text-primary">
                                {profile.profile_image ? (
                                    <img src={profile.profile_image} alt={profile.name} className="w-full h-full object-cover" />
                                ) : (
                                    profile.name.charAt(0).toUpperCase()
                                )}
                            </div>
                            <h1 className="text-2xl font-bold text-gray-900">{profile.name}</h1>
                            <p className="text-primary font-medium mt-1 capitalize">{profile.role}</p>

                            <div className="mt-8 space-y-4 text-left border-t pt-8">
                                <div className="flex items-center gap-3 text-gray-600">
                                    <Mail size={18} />
                                    <span className="truncate">{profile.email}</span>
                                </div>
                                {profile.role !== 'student' && (
                                    <div className="flex items-center gap-3 text-gray-600">
                                        <Award size={18} />
                                        <span>Expert {profile.role}</span>
                                    </div>
                                )}
                            </div>

                            {currentUser && currentUser.id === id && (
                                <Button
                                    className="w-full mt-8"
                                    variant="outline"
                                    onClick={() => navigate('/profile')}
                                >
                                    Edit Profile
                                </Button>
                            )}
                        </div>
                    </div>

                    {/* Main Content */}
                    <div className="md:col-span-2 space-y-8">
                        {/* Bio */}
                        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
                            <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                                <User size={20} className="text-primary" />
                                About
                            </h2>
                            <p className="text-gray-600 whitespace-pre-wrap leading-relaxed">
                                {profile.bio || "This user hasn't added a bio yet."}
                            </p>
                        </div>

                        {/* Courses (if instructor) */}
                        {(profile.role === 'instructor' || profile.role === 'admin') && (
                            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
                                <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                                    <BookOpen size={20} className="text-primary" />
                                    Courses by {profile.name}
                                </h2>

                                {profile.courses && profile.courses.length > 0 ? (
                                    <div className="grid sm:grid-cols-2 gap-6">
                                        {profile.courses.map((course) => (
                                            <div
                                                key={course.id}
                                                className="group border rounded-xl overflow-hidden hover:border-primary/50 transition-colors cursor-pointer"
                                                onClick={() => navigate(`/course/${course.id}`)}
                                            >
                                                <div className="aspect-video relative overflow-hidden bg-gray-100">
                                                    <img
                                                        src={course.thumbnail || '/placeholder-course.png'}
                                                        alt={course.title}
                                                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                                    />
                                                </div>
                                                <div className="p-4">
                                                    <h3 className="font-bold text-gray-900 line-clamp-1">{course.title}</h3>
                                                    <div className="mt-2 flex items-center justify-between">
                                                        <span className="text-sm text-gray-500">{course.category}</span>
                                                        <span className="font-bold text-primary">${course.price}</span>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-gray-500 italic">No courses published yet.</p>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
