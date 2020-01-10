%define kmod_name		ixgbevf
%define kmod_vendor		redhat
%define kmod_driver_version	3.2.2_k_rh7.4_z
%define kmod_rpm_release	1
%define kmod_kernel_version	3.10.0-514.el7
%define kmod_kbuild_dir		drivers/net/ethernet/intel/ixgbevf
%define kmod_dependencies       %{nil}

%{!?dist: %define dist .el7_3}

Source0:	%{kmod_name}-%{kmod_vendor}-%{kmod_driver_version}.tar.bz2
# Source code patches
Patch0:	0000-ixgbevf_backport_compat.patch
Patch1:	0001-skb_checksum_start.patch
Patch2:	0002-csum_replace_by_diff.patch
Patch3:	0003-fake-features.patch
Patch4:	0004-bump-version.patch

%define findpat %( echo "%""P" )
%define __find_requires /usr/lib/rpm/redhat/find-requires.ksyms
%define __find_provides /usr/lib/rpm/redhat/find-provides.ksyms %{kmod_name} %{?epoch:%{epoch}:}%{version}-%{release}
%define sbindir %( if [ -x "/sbin/weak-modules" ]; then echo "/sbin"; else echo %{_sbindir}; fi )

Name:		kmod-redhat-ixgbevf
Version:	%{kmod_driver_version}
Release:	%{kmod_rpm_release}%{?dist}
Summary:	ixgbevf module for Driver Update Program
Group:		System/Kernel
License:	GPLv2
URL:		http://www.kernel.org/
BuildRoot:	%(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildRequires:	kernel-devel = %kmod_kernel_version redhat-rpm-config kernel-abi-whitelists
ExclusiveArch:	x86_64
%global kernel_source() /usr/src/kernels/%{kmod_kernel_version}.$(arch)

%global _use_internal_dependency_generator 0
Provides:	kernel-modules = %kmod_kernel_version.%{_target_cpu}
Provides:	kmod-%{kmod_name} = %{?epoch:%{epoch}:}%{version}-%{release}
Requires(post):	%{sbindir}/weak-modules
Requires(postun):	%{sbindir}/weak-modules
Requires:	kernel >= 3.10.0-514.el7
Requires:	kernel < 3.10.0-515.el7
%if "%{kmod_dependencies}" != ""
Requires:       %{kmod_dependencies}
%endif
# if there are multiple kmods for the same driver from different vendors,
# they should conflict with each other.
Conflicts:	kmod-%{kmod_name}

%description
ixgbevf module for Driver Update Program

%if 0

%package -n kmod-redhat-ixgbevf-firmware
Version:	ENTER_FIRMWARE_VERSION
Summary:	ixgbevf firmware for Driver Update Program
Provides:	firmware(%{kmod_name}) = %{kmod_firmware_version}
Provides:	kernel-modules = %{kmod_kernel_version}.%{_target_cpu}
%description -n  kmod-redhat-ixgbevf-firmware
ixgbevf firmware for Driver Update Program


%files -n kmod-redhat-ixgbevf-firmware
%defattr(644,root,root,755)
%{FIRMWARE_FILES}

%endif

%post
modules=( $(find /lib/modules/%{kmod_kernel_version}.%(arch)/extra/kmod-%{kmod_vendor}-%{kmod_name} | grep '\.ko$') )
printf '%s\n' "${modules[@]}" | %{sbindir}/weak-modules --add-modules

%preun
rpm -ql kmod-redhat-ixgbevf-%{kmod_driver_version}-%{kmod_rpm_release}%{?dist}.$(arch) | grep '\.ko$' > /var/run/rpm-kmod-%{kmod_name}-modules

%postun
modules=( $(cat /var/run/rpm-kmod-%{kmod_name}-modules) )
rm /var/run/rpm-kmod-%{kmod_name}-modules
printf '%s\n' "${modules[@]}" | %{sbindir}/weak-modules --remove-modules

%files
%defattr(644,root,root,755)
/lib/modules/%{kmod_kernel_version}.%(arch)
/etc/depmod.d/%{kmod_name}.conf
/usr/share/doc/kmod-%{kmod_name}/greylist.txt

%prep
%setup -n %{kmod_name}-%{kmod_vendor}-%{kmod_driver_version}

%patch0 -p1
%patch1 -p1
%patch2 -p1
%patch3 -p1
%patch4 -p1
set -- *
mkdir source
mv "$@" source/
mkdir obj

%build
rm -rf obj
cp -r source obj
make -C %{kernel_source} M=$PWD/obj/%{kmod_kbuild_dir} \
	NOSTDINC_FLAGS="-I $PWD/obj/include"
# mark modules executable so that strip-to-file can strip them
find obj/%{kmod_kbuild_dir} -name "*.ko" -type f -exec chmod u+x '{}' +

whitelist="/lib/modules/kabi-current/kabi_whitelist_%{_target_cpu}"
for modules in $( find obj/%{kmod_kbuild_dir} -name "*.ko" -type f -printf "%{findpat}\n" | sed 's|\.ko$||' | sort -u ) ; do
	# update depmod.conf
	module_weak_path=$(echo $modules | sed 's/[\/]*[^\/]*$//')
	if [ -z "$module_weak_path" ]; then
		module_weak_path=%{name}
	else
		module_weak_path=%{name}/$module_weak_path
	fi
	echo "override $(echo $modules | sed 's/.*\///') $(echo %{kmod_kernel_version} | sed 's/\.[^\.]*$//').* weak-updates/$module_weak_path" >> source/depmod.conf

	# update greylist
	nm -u obj/%{kmod_kbuild_dir}/$modules.ko | sed 's/.*U //' |  sed 's/^\.//' | sort -u | while read -r symbol; do
		grep -q "^\s*$symbol\$" $whitelist || echo "$symbol" >> source/greylist
	done
done
sort -u source/greylist | uniq > source/greylist.txt

%install
export INSTALL_MOD_PATH=$RPM_BUILD_ROOT
export INSTALL_MOD_DIR=extra/%{name}
make -C %{kernel_source} modules_install \
	M=$PWD/obj/%{kmod_kbuild_dir}
# Cleanup unnecessary kernel-generated module dependency files.
find $INSTALL_MOD_PATH/lib/modules -iname 'modules.*' -exec rm {} \;

install -m 644 -D source/depmod.conf $RPM_BUILD_ROOT/etc/depmod.d/%{kmod_name}.conf
install -m 644 -D source/greylist.txt $RPM_BUILD_ROOT/usr/share/doc/kmod-%{kmod_name}/greylist.txt
%if 0
%{FIRMWARE_FILES_INSTALL}
%endif
%clean
rm -rf $RPM_BUILD_ROOT

%changelog
* Tue Apr 18 2017 Eugene Syromiatnikov <esyr@redhat.com> 3.2.2_k_rh7.4_z-1
- Resolves: #bz1441298
- 5e0df6596e78194c6dc5dd0a038302b7fbdfb4c3
- ixgbevf module for Driver Update Program
