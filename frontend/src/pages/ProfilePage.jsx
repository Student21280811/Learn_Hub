import React, { useState, useEffect } from 'react';
import axios from 'axios';
import Navbar from '@/components/Navbar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { User, Lock, Save, Camera } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function ProfilePage({ user, logout }) {
  const [profileData, setProfileData] = useState({
    name: user?.name || '',
    bio: user?.bio || '',
    profile_image: user?.profile_image || ''
  });

  const [passwordData, setPasswordData] = useState({
    old_password: '',
    new_password: '',
    confirm_password: ''
  });

  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) {
      setProfileData({
        name: user.name || '',
        bio: user.bio || '',
        profile_image: user.profile_image || ''
      });
    }
  }, [user]);

  const handleProfileUpdate = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.patch(`${API}/users/profile`, profileData);

      // Update local storage user data
      const updatedUser = { ...user, ...profileData };
      localStorage.setItem('user', JSON.stringify(updatedUser));

      toast.success('Profile updated successfully!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordUpdate = async (e) => {
    e.preventDefault();
    if (passwordData.new_password !== passwordData.confirm_password) {
      toast.error('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      await axios.patch(`${API}/users/profile/password`, {
        old_password: passwordData.old_password,
        new_password: passwordData.new_password
      });

      toast.success('Password updated successfully!');
      setPasswordData({ old_password: '', new_password: '', confirm_password: '' });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="profile-page" className="profile-page min-h-screen bg-gray-50">
      <Navbar user={user} logout={logout} />

      <div className="max-w-4xl mx-auto px-4 py-12 ml-auto mr-auto">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="bg-primary px-8 py-12 text-white">
            <div className="flex items-center gap-6">
              <div className="relative group">
                <div className="w-24 h-24 rounded-full border-4 border-white/20 bg-white/10 flex items-center justify-center text-3xl font-bold overflow-hidden">
                  {profileData.profile_image ? (
                    <img src={profileData.profile_image} alt={profileData.name} className="w-full h-full object-cover" />
                  ) : (
                    profileData.name.charAt(0).toUpperCase()
                  )}
                </div>
              </div>
              <div>
                <h1 className="text-3xl font-bold">{profileData.name}</h1>
                <p className="opacity-80 mt-1 capitalize">{user?.role} Profile</p>
              </div>
            </div>
          </div>

          <div className="p-8">
            <Tabs defaultValue="general" className="w-full">
              <TabsList className="bg-gray-100/50 p-1 mb-8">
                <TabsTrigger value="general" className="data-[state=active]:bg-white">
                  <User size={16} className="mr-2" />
                  General Information
                </TabsTrigger>
                <TabsTrigger value="security" className="data-[state=active]:bg-white">
                  <Lock size={16} className="mr-2" />
                  Security
                </TabsTrigger>
              </TabsList>

              <TabsContent value="general">
                <form onSubmit={handleProfileUpdate} className="grid gap-6 max-w-2xl">
                  <div className="grid gap-2">
                    <Label htmlFor="name">Full Name</Label>
                    <Input
                      id="name"
                      value={profileData.name}
                      onChange={(e) => setProfileData({ ...profileData, name: e.target.value })}
                      placeholder="Your Name"
                      required
                    />
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="bio">Bio</Label>
                    <Textarea
                      id="bio"
                      value={profileData.bio}
                      onChange={(e) => setProfileData({ ...profileData, bio: e.target.value })}
                      placeholder="Tell us about yourself..."
                      rows={5}
                    />
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="image">Profile Image URL</Label>
                    <div className="flex gap-4">
                      <Input
                        id="image"
                        value={profileData.profile_image}
                        onChange={(e) => setProfileData({ ...profileData, profile_image: e.target.value })}
                        placeholder="https://example.com/avatar.jpg"
                      />
                    </div>
                  </div>

                  <div className="pt-4">
                    <Button type="submit" disabled={loading} className="px-8">
                      {loading ? 'Saving...' : (
                        <>
                          <Save size={18} className="mr-2" />
                          Save Changes
                        </>
                      )}
                    </Button>
                  </div>
                </form>
              </TabsContent>

              <TabsContent value="security">
                <form onSubmit={handlePasswordUpdate} className="grid gap-6 max-w-2xl">
                  <div className="grid gap-2">
                    <Label htmlFor="old_password">Current Password</Label>
                    <Input
                      id="old_password"
                      type="password"
                      value={passwordData.old_password}
                      onChange={(e) => setPasswordData({ ...passwordData, old_password: e.target.value })}
                      placeholder="••••••••"
                      required
                    />
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="grid gap-2">
                      <Label htmlFor="new_password">New Password</Label>
                      <Input
                        id="new_password"
                        type="password"
                        value={passwordData.new_password}
                        onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })}
                        placeholder="••••••••"
                        required
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="confirm_password">Confirm New Password</Label>
                      <Input
                        id="confirm_password"
                        type="password"
                        value={passwordData.confirm_password}
                        onChange={(e) => setPasswordData({ ...passwordData, confirm_password: e.target.value })}
                        placeholder="••••••••"
                        required
                      />
                    </div>
                  </div>

                  <div className="pt-4">
                    <Button type="submit" disabled={loading} className="px-8">
                      {loading ? 'Updating...' : (
                        <>
                          <Lock size={18} className="mr-2" />
                          Update Password
                        </>
                      )}
                    </Button>
                  </div>
                </form>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>
    </div>
  );
}