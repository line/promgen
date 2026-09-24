Permissions
===========

Promgen supports managing user permissions on specific resources.
This allows fine-grained control over who can view or modify certain objects of Promgen.
Permissions can be assigned to users or groups (see: :ref:`group`).

.. image:: /images/members_panel.png

Service and Project permissions
-------------------------------
Any authenticated user can create a **new Service** on Promgen. After creating a Service or Project,
the user will automatically become the **Owner** of the object as well as the first **Admin**.
The Admin can do most of the operations on the object, including modifying its content and managing
permissions for other users or groups. However, only the Owner can **delete** or **transfer ownership**
of the object.

Permissions can be assigned at both the **Service** and **Project** levels.

Each user or group can have at most one permission per Service or Project: **Admin**, **Editor** and **Viewer**.

- **Admin**: Has full control over the Service or Project, including managing permissions.
- **Editor**: Can modify the Service's or Project's content.
- **Viewer**: Has read-only access to the Service or Project.


Inheritance of Permissions
--------------------------
In Promgen, an object could be the child of others. For example, a Project belongs to a Service, or an Exporter belongs to a Project.

.. image:: /images/inheritance_of_models.png

The permissions are **inherited**. This means the person who has a specific permission on the parent object will have that permission on all the children objects.
For example, if a user has Admin permission on a Service, they will automatically have Admin permission on all Projects under that Service.

To keep it simple, an **Editor** can fully control child objects, **unless** the child is a Project.
It means if someone has Editor permission for a Service, they can change and even **delete** all its Rules and Notifiers.

The following table summarizes the permissions inheritance:

.. list-table::
   :header-rows: 1

   * - Role|Target
     - Service
     - Service's Notifier/Rule
     - Service's Project
     - | Project's Notifier/Rule/
       | Exporter/URL/Farm/Host
   * - Service's Owner
     - * View/Edit/Delete
       * Transfer ownership
       * Manage members
     - * Create/View/Edit/Delete
     - * Create/View/Edit/Delete
       * Transfer ownership
       * Manage members
     - * Create/View/Edit/Delete
   * - Service's Admin
     - * View/Edit
       * Manage members
     - * Create/View/Edit/Delete
     - * Create/View/Edit
       * Manage members
     - * Create/View/Edit/Delete
   * - Service's Editor
     - * Create/View/Edit
     - * Create/View/Edit/Delete
     - * Create/View/Edit
     - * Create/View/Edit/Delete
   * - Service's Viewer
     - * View
     - * View
     - * View
     - * View
   * - Project's Owner
     -
     -
     - * View/Edit/Delete
       * Transfer ownership
       * Manage members
     - * Create/View/Edit/Delete
   * - Project's Admin
     -
     -
     - * View/Edit
       * Manage members
     - * Create/View/Edit/Delete
   * - Project's Editor
     -
     -
     - * View/Edit
     - * Create/View/Edit/Delete
   * - Project's Viewer
     -
     -
     - * View
     - * View


**Use cases:**

- User with **Service Admin** permission can manage all aspects of the Service, including its Projects and associated objects, but only the owner can delete the Service or any Project.
- User with **Project Admin** permission can manage the specific Project and its associated objects, but only the owner can delete the Service or any Project.
  Also, a Project Admin cannot see or modify other Projects under the same Service. They cannot even view the parent Service's details unless they have explicit permissions on that Service.
- User with **Service Viewer** permission can only view all aspects of the Service, including its Projects and associated objects, without making any changes.
- User with **Project Viewer** permission can only view the specific Project and its associated objects, but cannot see or modify other Projects under the same Service.
- User with **Service Editor** permission can modify the Service, its associated objects and the Projects under that Service, but cannot delete those Projects. However, they still can delete any associated objects of those Projects (such as Exporters and Farms).
- User with **Project Editor** permission can modify the specific Project and its associated objects. They can also delete associated objects of that Project (such as Exporters and Farms), but cannot delete the Project itself. In addition, they don't have any permissions on other Projects under the same Service.
