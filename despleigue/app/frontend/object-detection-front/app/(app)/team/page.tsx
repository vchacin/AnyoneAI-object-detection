"use client";

import { PageHeader } from "@/components/common/page-header";
import { RequireStore } from "@/components/common/require-store";
import { EmployeesTab } from "@/components/team/employees-tab";
import { ShiftsTab } from "@/components/team/shifts-tab";
import { UsersTab } from "@/components/team/users-tab";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function TeamPage() {
  return (
    <>
      <PageHeader title="Team" description="Access accounts, store staff, and their weekly schedules." />
      <RequireStore>
        {(storeId) => (
          <Tabs defaultValue="users">
            <TabsList className="mb-5">
              <TabsTrigger value="users">Users</TabsTrigger>
              <TabsTrigger value="employees">Employees</TabsTrigger>
              <TabsTrigger value="shifts">Shifts</TabsTrigger>
            </TabsList>
            <TabsContent value="users"><UsersTab key={storeId} storeId={storeId} /></TabsContent>
            <TabsContent value="employees"><EmployeesTab key={storeId} storeId={storeId} /></TabsContent>
            <TabsContent value="shifts"><ShiftsTab key={storeId} storeId={storeId} /></TabsContent>
          </Tabs>
        )}
      </RequireStore>
    </>
  );
}
