import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { getErrorMessage } from "../../api/errors";
import {
  changePassword,
  updateUserProfile,
} from "../../api/user";
import { LoadingBlock } from "../../components/LoadingBlock";
import { AuthGate } from "../auth/AuthGate";
import { useAuth } from "../auth/useAuth";

type ProfileFormState = {
  avatar: string;
  bio: string;
  gender: string;
  nickname: string;
  phone: string;
};

const EMPTY_FORM: ProfileFormState = {
  avatar: "",
  bio: "",
  gender: "",
  nickname: "",
  phone: "",
};

export function ProfilePage() {
  const { isAuthenticated, isRefreshingUser, syncUser, user } = useAuth();
  const [profileForm, setProfileForm] = useState<ProfileFormState>(
    EMPTY_FORM,
  );
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [profileMessage, setProfileMessage] = useState<string | null>(
    null,
  );
  const [passwordMessage, setPasswordMessage] = useState<string | null>(
    null,
  );

  const profileMutation = useMutation({
    mutationFn: updateUserProfile,
    onSuccess: (nextUser) => {
      syncUser(nextUser);
      setProfileMessage("资料已更新");
    },
  });

  const passwordMutation = useMutation({
    mutationFn: changePassword,
    onSuccess: () => {
      setPasswordMessage("密码修改成功");
      setOldPassword("");
      setNewPassword("");
    },
  });

  useEffect(() => {
    if (!user) {
      return;
    }

    setProfileForm({
      avatar: user.avatar ?? "",
      bio: user.bio ?? "",
      gender: user.gender ?? "",
      nickname: user.nickname ?? "",
      phone: user.phone ?? "",
    });
  }, [user]);

  if (!isAuthenticated) {
    return (
      <div className="page">
        <AuthGate
          title="登录后查看个人中心"
          description="这里可以维护头像、昵称、手机号和密码。"
        />
      </div>
    );
  }

  if (!user && isRefreshingUser) {
    return (
      <div className="page">
        <LoadingBlock label="正在读取个人资料..." />
      </div>
    );
  }

  return (
    <div className="page page--profile">
      <section className="page-head">
        <div>
          <p className="eyebrow">Profile</p>
          <h1>个人中心</h1>
          <p>维护你的公开资料与登录密码。</p>
        </div>
      </section>

      <div className="profile-grid">
        <section className="profile-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Profile</p>
              <h2>基础资料</h2>
            </div>
          </div>

          <form
            className="profile-form"
            onSubmit={(event) => {
              event.preventDefault();
              setProfileMessage(null);
              void profileMutation.mutateAsync({
                avatar: profileForm.avatar || undefined,
                bio: profileForm.bio || undefined,
                gender: profileForm.gender || undefined,
                nickname: profileForm.nickname || undefined,
                phone: profileForm.phone || undefined,
              }).catch((error) => {
                setProfileMessage(getErrorMessage(error));
              });
            }}
          >
            <label className="profile-form__field">
              <span>用户名</span>
              <input value={user?.username ?? ""} disabled />
            </label>
            <label className="profile-form__field">
              <span>昵称</span>
              <input
                value={profileForm.nickname}
                onChange={(event) =>
                  setProfileForm((current) => ({
                    ...current,
                    nickname: event.target.value,
                  }))
                }
              />
            </label>
            <label className="profile-form__field">
              <span>头像 URL</span>
              <input
                value={profileForm.avatar}
                onChange={(event) =>
                  setProfileForm((current) => ({
                    ...current,
                    avatar: event.target.value,
                  }))
                }
              />
            </label>
            <label className="profile-form__field">
              <span>手机号</span>
              <input
                value={profileForm.phone}
                onChange={(event) =>
                  setProfileForm((current) => ({
                    ...current,
                    phone: event.target.value,
                  }))
                }
              />
            </label>
            <label className="profile-form__field">
              <span>性别</span>
              <select
                value={profileForm.gender}
                onChange={(event) =>
                  setProfileForm((current) => ({
                    ...current,
                    gender: event.target.value,
                  }))
                }
              >
                <option value="">未设置</option>
                <option value="male">男</option>
                <option value="female">女</option>
                <option value="unknown">保密</option>
              </select>
            </label>
            <label className="profile-form__field profile-form__field--full">
              <span>个人简介</span>
              <textarea
                value={profileForm.bio}
                onChange={(event) =>
                  setProfileForm((current) => ({
                    ...current,
                    bio: event.target.value,
                  }))
                }
              />
            </label>

            {profileMessage ? (
              <p className="profile-form__message">{profileMessage}</p>
            ) : null}

            <button
              type="submit"
              className="button button--primary"
              disabled={profileMutation.isPending}
            >
              {profileMutation.isPending ? "保存中..." : "保存资料"}
            </button>
          </form>
        </section>

        <section className="profile-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Security</p>
              <h2>修改密码</h2>
            </div>
          </div>

          <form
            className="profile-form"
            onSubmit={(event) => {
              event.preventDefault();
              setPasswordMessage(null);
              void passwordMutation.mutateAsync({
                oldPassword,
                newPassword,
              }).catch((error) => {
                setPasswordMessage(getErrorMessage(error));
              });
            }}
          >
            <label className="profile-form__field">
              <span>旧密码</span>
              <input
                type="password"
                value={oldPassword}
                onChange={(event) => setOldPassword(event.target.value)}
              />
            </label>
            <label className="profile-form__field">
              <span>新密码</span>
              <input
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
              />
            </label>

            {passwordMessage ? (
              <p className="profile-form__message">{passwordMessage}</p>
            ) : null}

            <button
              type="submit"
              className="button button--primary"
              disabled={passwordMutation.isPending}
            >
              {passwordMutation.isPending ? "提交中..." : "更新密码"}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
